"""
Keycloak OIDC Authentication Module.

Provides JWT verification via JWKS and role-based access control for FastAPI.
Uses Keycloak as the Identity Provider (IdP) with OpenID Connect.
"""

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.orm_models.models import User
from database.orm_models.roles import Role
from shared_libraries.config import get_settings
from shared_libraries.database import get_db
from shared_libraries.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(
    scheme_name="Keycloak JWT",
    description="JWT Bearer token from Keycloak",
    auto_error=True,
)


class TokenPayload(BaseModel):
    """Validated JWT token payload."""

    sub: str  # Subject (user ID)
    email: str | None = None
    preferred_username: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    realm_access: dict | None = None
    resource_access: dict | None = None
    exp: int
    iat: int
    iss: str
    aud: Any | None = None


class CurrentUser(BaseModel):
    """Represents the authenticated user."""

    id: str  # Keycloak user ID (sub claim)
    email: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    roles: list[str] = []
    permissions: list[str] = []

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role("admin")

    def has_permission(self, permission: str) -> bool:
        """Check for granular permission."""
        if "*" in self.permissions:
            return True
        if permission in self.permissions:
            return True
        resource, _ = (
            permission.split(":", 1) if ":" in permission else (permission, "")
        )
        if f"{resource}:*" in self.permissions:
            return True
        return False


class JWKSClient:
    """JSON Web Key Set client for fetching and caching public keys."""

    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._keys: dict = {}
        self._last_fetch: datetime | None = None

    async def get_key(self, kid: str) -> dict | None:
        if self._should_refresh() or kid not in self._keys:
            await self._fetch_keys()
        return self._keys.get(kid)

    def _should_refresh(self) -> bool:
        if self._last_fetch is None:
            return True
        elapsed = (datetime.now(UTC) - self._last_fetch).total_seconds()
        return elapsed > self.cache_ttl

    async def _fetch_keys(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()
            self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
            self._last_fetch = datetime.now(UTC)
            logger.debug("jwks_refreshed", key_count=len(self._keys))
        except Exception as e:
            logger.error("jwks_fetch_failed", error=str(e))
            if not self._keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to fetch authentication keys",
                ) from None


_jwks_client: JWKSClient | None = None


def get_jwks_client() -> JWKSClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = JWKSClient(settings.keycloak_jwks_url)
    return _jwks_client


def extract_roles(payload: TokenPayload) -> list[str]:
    """Extract roles from both realm and resource access claims."""
    roles = set()
    if payload.realm_access:
        realm_roles = payload.realm_access.get("roles", [])
        roles.update(realm_roles)
    if payload.resource_access:
        client_roles = payload.resource_access.get(settings.keycloak_client_id, {}).get(
            "roles", []
        )
        roles.update(client_roles)

    internal_roles = {
        "offline_access",
        "uma_authorization",
        f"default-roles-{settings.keycloak_realm}",
    }
    return list(roles - internal_roles)


async def verify_token(token: str) -> TokenPayload:
    """Verify the JWT token and return the payload."""
    print(f"DEBUG: verify_token called with token prefix: {token[:10]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        unverified_header = jwt.get_unverified_header(token)
        print(f"DEBUG: unverified_header: {unverified_header}")
        kid = unverified_header.get("kid")
        if not kid:
            logger.warning("token_verification_failed_no_kid", header=unverified_header)
            raise credentials_exception

        jwks_client = get_jwks_client()
        key_data = await jwks_client.get_key(kid)
        if not key_data:
            logger.warning(
                "token_verification_failed_key_not_found",
                kid=kid,
                available_kids=list(jwks_client._keys.keys()),
            )
            raise credentials_exception

        public_key = jwk.construct(key_data)
        
        # Verify, but handle potential issuer mismatch due to Docker networking
        # Frontend sees localhost:8080, Backend sees keycloak:8080
        options = {
            "verify_aud": False,
            "verify_iss": False, # We will manually check issuer
            "verify_exp": True,
            "verify_iat": True,
        }
        
        payload_dict = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            options=options,
        )
        
        # Manual Issuer Check
        iss = payload_dict.get("iss")
        expected_issKeycloak = settings.keycloak_issuer
        # Create an alternative valid issuer for localhost
        expected_issLocal = expected_issKeycloak.replace("http://keycloak:8080", "http://localhost:8080")
        
        if iss not in [expected_issKeycloak, expected_issLocal]:
             logger.warning("token_verification_failed_issuer_mismatch", iss=iss, expected=[expected_issKeycloak, expected_issLocal])
             raise credentials_exception

        return TokenPayload(**payload_dict)
        return TokenPayload(**payload_dict)
    except Exception as e:
        logger.warning("token_verification_failed", error=str(e))
        raise credentials_exception from None


class Permissions:
    """System permissions constants."""

    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    PATIENT_READ = "patient:read"
    PATIENT_WRITE = "patient:write"
    PATIENT_ADMIT = "patient:admit"
    PATIENT_DISCHARGE = "patient:discharge"
    GATE_READ = "gate:read"
    GATE_CONTROL = "gate:control"
    ZONE_READ = "zone:read"
    ZONE_WRITE = "zone:write"
    RTLS_READ = "rtls:read"
    RTLS_HISTORY = "rtls:history"
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIG = "system:config"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db=Depends(get_db),
) -> CurrentUser:
    """Get the current authenticated user with DB-backed roles/permissions."""
    token = credentials.credentials
    payload = await verify_token(token)

    try:
        user_uuid = payload.sub
        query = (
            select(User).where(User.id == user_uuid).options(selectinload(User.role))
        )
        result = await db.execute(query)
        db_user = result.scalar_one_or_none()

        # JIT Provisioning: If user doesn't exist, create them
        if not db_user:
            logger.info("jit_provisioning_user", user_id=user_uuid, email=payload.email)

            # Find viewer role (Safe default)
            role_query = select(Role).where(Role.name == "viewer")
            role_result = await db.execute(role_query)
            default_role = role_result.scalar_one_or_none()

            if not default_role:
                # If viewer doesn't exist, try getting any non-admin role, or create viewer?
                # For now, let's just log verification warning and fail safe or use a safe fallback.
                # Do NOT default to admin.
                fallback_query = select(Role).where(Role.name != "admin").limit(1)
                fallback_result = await db.execute(fallback_query)
                default_role = fallback_result.scalar_one_or_none()

            # Safe username generation
            email = payload.email or ""
            username = payload.preferred_username
            if not username and email:
                username = email.split("@")[0]
            if not username:
                username = f"user_{user_uuid[:8]}"

            new_user = User(
                id=user_uuid,
                email=email,
                # username field does not exist in User model
                first_name=payload.given_name or "",
                last_name=payload.family_name or "",
                hashed_password="OIDC_LOGIN_NO_PASSWORD",  # Placeholder for OIDC users
                is_active=True,
                role_id=default_role.id if default_role else None,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            # Re-fetch with relationship
            query = (
                select(User)
                .where(User.id == user_uuid)
                .options(selectinload(User.role))
            )
            result = await db.execute(query)
            db_user = result.scalar_one_or_none()

        effective_roles = []
        effective_permissions = []

        if db_user and db_user.role:
            effective_roles = [db_user.role.name]
            perms = db_user.role.permissions
            if perms:
                for resource, actions in perms.items():
                    if resource == "*":
                        if "*" in actions:
                            effective_permissions.append("*")
                        else:
                            for action in actions:
                                effective_permissions.append(f"*:{action}")
                    else:
                        for action in actions:
                            effective_permissions.append(f"{resource}:{action}")
        else:
            effective_roles = extract_roles(payload)

    except Exception as e:
        logger.error("auth_db_lookup_failed", error=str(e))
        await db.rollback()  # Ensure session is clean for subsequent requests
        effective_roles = extract_roles(payload)
        effective_permissions = []

    return CurrentUser(
        id=payload.sub,
        email=payload.email,
        username=payload.preferred_username,
        first_name=payload.given_name,
        last_name=payload.family_name,
        roles=effective_roles,
        permissions=effective_permissions,
    )


def require_roles(required_roles: list[str], require_all: bool = False):
    """Dependency requiring specific roles."""

    async def role_checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if require_all:
            has_required = all(role in user.roles for role in required_roles)
        else:
            has_required = any(role in user.roles for role in required_roles)

        if not has_required:
            logger.warning(
                "access_denied_role",
                user=user.id,
                roles=user.roles,
                required=required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions (Role)",
            )
        return user

    return role_checker


def require_permission(permission: str):
    """Dependency requiring a specific granular permission."""

    async def permission_checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_permission(permission):
            logger.warning(
                "access_denied_permission", user_id=user.id, permission=permission
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission}",
            )
        return user

    return permission_checker


# Pre-configured dependencies
require_admin = require_roles(["admin"])
require_user_or_admin = require_roles(["user", "admin"])
require_audit_read = require_permission(Permissions.AUDIT_READ)

bearer_scheme_optional = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme_optional),
) -> CurrentUser | None:
    if not credentials:
        return None
    try:
        from shared_libraries.database import async_session_factory

        async with async_session_factory() as db:
            token = credentials.credentials
            await verify_token(token)
            return await get_current_user(credentials, db)
    except Exception:
        return None
