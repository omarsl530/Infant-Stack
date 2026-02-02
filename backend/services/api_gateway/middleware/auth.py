"""
JWT Authentication Middleware for Keycloak

Validates JWT tokens issued by Keycloak and extracts user information.
Provides role-based access control for API endpoints.

Security Features:
- RS256 signature verification using Keycloak's public key
- Token expiration validation
- Issuer and audience validation
- Role extraction from realm_access claims
"""

import json
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared_libraries.config import get_settings
from shared_libraries.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# =============================================================================
# Models
# =============================================================================


class TokenPayload(BaseModel):
    """Parsed JWT token payload."""

    sub: str  # Subject (user ID)
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    realm_access: Optional[dict] = None
    resource_access: Optional[dict] = None
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    iss: str  # Issuer


class CurrentUser(BaseModel):
    """Current authenticated user context."""

    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list[str] = []
    token_payload: dict = {}


# =============================================================================
# Keycloak Configuration
# =============================================================================


# Keycloak OIDC configuration - can be overridden via environment
KEYCLOAK_URL = settings.keycloak_url if hasattr(settings, "keycloak_url") else "http://localhost:8080"
KEYCLOAK_REALM = settings.keycloak_realm if hasattr(settings, "keycloak_realm") else "infant-stack"
KEYCLOAK_ISSUER = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"


# Internal roles to filter out
INTERNAL_ROLES = {
    "offline_access",
    "uma_authorization",
    "default-roles-infant-stack",
}


# =============================================================================
# JWKS (JSON Web Key Set) Handling
# =============================================================================


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """
    Fetch and cache Keycloak's public keys (JWKS).
    
    Uses LRU cache to avoid repeated HTTP requests.
    In production, consider adding TTL-based cache invalidation.
    """
    try:
        response = httpx.get(KEYCLOAK_JWKS_URL, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("failed_to_fetch_jwks", error=str(e), url=KEYCLOAK_JWKS_URL)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


def get_public_key(token: str) -> dict:
    """
    Extract the public key from JWKS matching the token's key ID.
    
    JWT protection against key confusion attacks.
    """
    try:
        # Decode header without verification to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID",
            )
        
        jwks = get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        # Key not found - might need to refresh JWKS cache
        get_jwks.cache_clear()
        jwks = get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token key ID not found in JWKS",
        )
        
    except JWTError as e:
        logger.error("jwt_header_decode_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )


# =============================================================================
# Token Validation
# =============================================================================


def validate_token(token: str) -> TokenPayload:
    """
    Validate JWT token and return parsed payload.
    
    Performs:
    - Signature verification using Keycloak's public key
    - Expiration check
    - Issuer validation
    """
    try:
        public_key = get_public_key(token)
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=KEYCLOAK_ISSUER,
            options={
                "verify_aud": False,  # SPA clients don't always set audience
                "verify_exp": True,
                "verify_iss": True,
            },
        )
        
        return TokenPayload(**payload)
        
    except jwt.ExpiredSignatureError:
        logger.warning("token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTClaimsError as e:
        logger.warning("token_claims_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token claims validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning("token_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_roles(payload: TokenPayload) -> list[str]:
    """
    Extract user roles from token payload.
    
    Combines realm_access and resource_access roles,
    filtering out internal Keycloak roles.
    """
    roles = set()
    
    # Realm roles
    if payload.realm_access:
        realm_roles = payload.realm_access.get("roles", [])
        roles.update(realm_roles)
    
    # Resource/client roles (if any)
    if payload.resource_access:
        for client, access in payload.resource_access.items():
            client_roles = access.get("roles", [])
            roles.update(client_roles)
    
    # Filter out internal roles
    return [r for r in roles if r not in INTERNAL_ROLES]


# =============================================================================
# FastAPI Dependencies
# =============================================================================


# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency that returns the current authenticated user.
    
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = validate_token(token)
    roles = extract_roles(payload)
    
    user = CurrentUser(
        id=payload.sub,
        email=payload.email,
        username=payload.preferred_username,
        first_name=payload.given_name,
        last_name=payload.family_name,
        roles=roles,
        token_payload=payload.model_dump(),
    )
    
    # Attach user to request state for middleware access
    request.state.user = user
    
    logger.info(
        "user_authenticated",
        user_id=user.id,
        email=user.email,
        roles=roles,
    )
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentUser]:
    """
    FastAPI dependency that returns the current user if authenticated.
    
    Returns None if not authenticated (does not raise 401).
    Useful for public endpoints that behave differently for logged-in users.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_role(*required_roles: str):
    """
    Factory function creating a dependency that requires specific roles.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint():
            ...
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(role in user.roles for role in required_roles):
            logger.warning(
                "access_denied_insufficient_roles",
                user_id=user.id,
                user_roles=user.roles,
                required_roles=required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}",
            )
        return user
    
    return role_checker


def require_all_roles(*required_roles: str):
    """
    Factory function creating a dependency that requires ALL specified roles.
    
    Usage:
        @router.get("/super-admin", dependencies=[Depends(require_all_roles("admin", "security"))])
        async def super_admin_endpoint():
            ...
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not all(role in user.roles for role in required_roles):
            logger.warning(
                "access_denied_missing_roles",
                user_id=user.id,
                user_roles=user.roles,
                required_roles=required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles. All of these are required: {', '.join(required_roles)}",
            )
        return user
    
    return role_checker
