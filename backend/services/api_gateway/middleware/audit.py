import time
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared_libraries.database import session_factory
from shared_libraries.logging import get_logger
from shared_libraries.auth import verify_token
from database.orm_models.models import AuditLog

logger = get_logger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to audit log non-GET requests.
    
    Captures:
    - User ID (from Authorization header)
    - Action (HTTP Method)
    - Resource (URL Path)
    - IP Address
    - Status Code
    - Duration
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Determine if we should log based on method (skip GET/OPTIONS/HEAD)
        # We can make this configurable, for now log state-changing methods
        should_log = request.method in ["POST", "PUT", "PATCH", "DELETE"]
        
        # Execute request
        response = await call_next(request)
        
        if not should_log:
            return response
            
        # Collect log data
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code
        path = request.url.path
        method = request.method
        ip = request.client.host if request.client else None
        
        # Extract User ID from Token
        user_id: Optional[UUID] = None
        user_details = {}
        
        try:
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                token = auth.split(" ")[1]
                # Verify token to get claims
                payload = await verify_token(token)
                try:
                    user_id = UUID(payload.sub)
                except ValueError:
                    user_details["sub_raw"] = payload.sub
        except Exception as e:
            # Token invalid or verify failed - log simply as anonymous but record error
            logger.debug("audit_token_verify_failed", error=str(e))
            
        # Log to Database (async fire-and-forget style to not block response too much)
        # We await it here to ensure data safety, but it adds ms to latency.
        # Alternatively use BackgroundTasks but middleware dispatch returns Response immediately.
        try:
            await self._log_to_db(user_id, method, "api_gateway", path, ip, status_code, duration_ms, user_details)
        except Exception as e:
            logger.error("audit_log_write_failed", error=str(e))
            
        return response

    async def _log_to_db(
        self,
        user_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: str,
        ip: Optional[str],
        status_code: int,
        duration_ms: int,
        extra_details: dict
    ):
        async with session_factory() as db:
            details = {
                "status_code": status_code,
                "duration_ms": duration_ms,
                **extra_details
            }
            
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip,
                details=details
            )
            
            db.add(log_entry)
            
            try:
                await db.commit()
            except Exception as e:
                # Handle potential FK violation if user_id doesn't exist in local DB
                if user_id and "ForeignKeyViolation" in str(e) or "foreign key constraint" in str(e).lower():
                    await db.rollback()
                    # Retry with user_id=None
                    log_entry.user_id = None
                    log_entry.details["original_user_id"] = str(user_id)
                    log_entry.details["fk_error"] = "User not found in local DB"
                    db.add(log_entry)
                    await db.commit()
                else:
                    raise e
