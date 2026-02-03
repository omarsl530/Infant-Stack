import time
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from database.orm_models.models import AuditLog
from shared_libraries.auth import verify_token
from shared_libraries.database import session_factory
from shared_libraries.logging import get_logger

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
    
    async def _update_last_seen(self, user_id: UUID):
        """
        Update the last_login timestamp for a user.
        Also infers a 'login' audit event if user was inactive for > 15 minutes.
        """
        try:
             async with session_factory() as db:
                from database.orm_models.models import User, AuditLog
                from datetime import datetime, timedelta, timezone
                from sqlalchemy import select
                
                # 1. Fetch current last_login
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return

                # Use timezone-aware UTC to match database typically returning offset-aware for TIMESTAMPTZ
                now = datetime.now(timezone.utc)
                # Lower threshold to 1 minute for testing/demo purposes so user sees logs more easily
                threshold = timedelta(minutes=1)
                
                # 2. Check if we should log a "login" event
                should_log_login = False
                
                last_login = user.last_login
                # Handle case where DB might return naive (if configured differently) or user.last_login is None
                if last_login:
                    if last_login.tzinfo is None:
                        # Ensure we compare apples to apples if DB returns naive
                        last_login = last_login.replace(tzinfo=timezone.utc)
                
                    if (now - last_login > threshold):
                        should_log_login = True
                else:
                    should_log_login = True
                    
                # 3. Update last_login
                update_threshold = timedelta(minutes=1)
                
                # Check update threshold
                should_update_db = should_log_login or not last_login
                if not should_update_db and last_login:
                     if (now - last_login > update_threshold):
                         should_update_db = True
                
                if should_update_db:
                    user.last_login = now
                    db.add(user) # Mark as modified
                    
                    if should_log_login:
                        # Create implicit login audit log
                        login_log = AuditLog(
                            user_id=user_id,
                            action="login",
                            resource_type="auth",
                            resource_id=str(user_id),
                            details={"method": "implicit_session_start", "inferred": True},
                            ip_address=None # We don't have IP easily here without passing it down, acceptable for now
                        )
                        db.add(login_log)
                    
                    await db.commit()
                    
        except Exception as e:
            # Swallow errors here to not impact request
            logger.debug("last_seen_update_failed", error=str(e))

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # 1. Initialize variables & Extract User ID from Token
        user_id: UUID | None = None
        user_details = {}

        try:
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                token = auth.split(" ")[1]
                payload = await verify_token(token)
                try:
                    user_id = UUID(payload.sub)
                except ValueError:
                    user_details["sub_raw"] = payload.sub
        except Exception as e:
            logger.debug("audit_token_verify_failed", error=str(e))

        # 2. Determine if we should audit log
        should_log = request.method in ["POST", "PUT", "PATCH", "DELETE"]

        # 3. Execute request
        response = await call_next(request)

        # 4. Update Last Seen (if authenticated)
        # We do this regardless of method, but maybe debounce or async it?
        # If we log to DB (should_log=True), we can do it there to save a separate commit if we wanted,
        # but reusing the helper is cleaner.
        if user_id:
             try:
                 # Fire and forget-ish (we await it, so it adds latency, but ensures consistency)
                 await self._update_last_seen(user_id)
             except Exception:
                 pass

        # 5. Handle early exit for non-audited requests
        if not should_log:
            return response

        # 6. Audit Logging
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code
        path = request.url.path
        method = request.method
        ip = request.client.host if request.client else None

        try:
            await self._log_to_db(
                user_id,
                method,
                "api_gateway",
                path,
                ip,
                status_code,
                duration_ms,
                user_details,
            )
        except Exception as e:
            logger.error("audit_log_write_failed", error=str(e))

        return response

    async def _log_to_db(
        self,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        ip: str | None,
        status_code: int,
        duration_ms: int,
        extra_details: dict,
    ):
        async with session_factory() as db:
            details = {
                "status_code": status_code,
                "duration_ms": duration_ms,
                **extra_details,
            }

            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip,
                details=details,
            )

            db.add(log_entry)

            try:
                await db.commit()
            except Exception as e:
                # Handle potential FK violation if user_id doesn't exist in local DB
                if (
                    user_id
                    and "ForeignKeyViolation" in str(e)
                    or "foreign key constraint" in str(e).lower()
                ):
                    await db.rollback()
                    # Retry with user_id=None
                    log_entry.user_id = None
                    log_entry.details["original_user_id"] = str(user_id)
                    log_entry.details["fk_error"] = "User not found in local DB"
                    db.add(log_entry)
                    await db.commit()
                else:
                    raise e


