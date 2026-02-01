"""
Keycloak OIDC Authentication Module.

Provides JWT verification via JWKS and role-based access control for FastAPI.
Uses Keycloak as the Identity Provider (IdP) with OpenID Connect.
"""

import httpx
from functools import lru_cache
from typing import Optional, List, Any
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, jwk, JWTError
from jose.exceptions import JWKError

from shared_libraries.config import get_settings
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
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    realm_access: Optional[dict] = None
    resource_access: Optional[dict] = None
    exp: int
    iat: int
    iss: str
    aud: Optional[Any] = None  # Can be string or list


class CurrentUser(BaseModel):
    """Represents the authenticated user."""
    id: str  # Keycloak user ID (sub claim)
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = []

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.has_role("admin")


class JWKSClient:
    """
    JWKS (JSON Web Key Set) client for fetching and caching public keys.
    
    Fetches keys from Keycloak's JWKS endpoint and caches them for verification.
    Keys are refreshed when a new key ID is encountered or on cache expiration.
    """
    
    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._keys: dict = {}
        self._last_fetch: Optional[datetime] = None

    async def get_key(self, kid: str) -> Optional[dict]:
        """
        Get the public key for a given key ID.
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            JWK key dict or None if not found
        """
        # Refresh cache if expired or key not found
        if self._should_refresh() or kid not in self._keys:
            await self._fetch_keys()
        
        return self._keys.get(kid)

    def _should_refresh(self) -> bool:
        """Check if cache should be refreshed."""
        if self._last_fetch is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_fetch).total_seconds()
        return elapsed > self.cache_ttl

    async def _fetch_keys(self) -> None:
        """Fetch JWKS from Keycloak endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()
                
            self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
            self._last_fetch = datetime.now(timezone.utc)
            logger.debug("jwks_refreshed", key_count=len(self._keys))
        except Exception as e:
            logger.error("jwks_fetch_failed", error=str(e))
            # Keep existing keys on fetch failure
            if not self._keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to fetch authentication keys",
                )


# Global JWKS client instance
_jwks_client: Optional[JWKSClient] = None


def get_jwks_client() -> JWKSClient:
    """Get or create the global JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = JWKSClient(settings.keycloak_jwks_url)
    return _jwks_client


def extract_roles(payload: TokenPayload) -> List[str]:
    """
    Extract roles from token payload.
    
    Checks both realm_access.roles and resource_access.{client_id}.roles
    to support different Keycloak configurations.
    
    Args:
        payload: Validated token payload
        
    Returns:
        List of role names
    """
    roles = set()
    
    # Extract from realm_access.roles
    if payload.realm_access:
        realm_roles = payload.realm_access.get("roles", [])
        roles.update(realm_roles)
    
    # Extract from resource_access.{client_id}.roles
    if payload.resource_access:
        client_roles = payload.resource_access.get(
            settings.keycloak_client_id, {}
        ).get("roles", [])
        roles.update(client_roles)
    
    # Remove Keycloak internal roles
    internal_roles = {"offline_access", "uma_authorization", "default-roles-infant-stack"}
    roles = roles - internal_roles
    
    return list(roles)


async def verify_token(token: str) -> TokenPayload:
    """
    Verify JWT token signature and claims.
    
    Args:
        token: JWT access token string
        
    Returns:
        Validated token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            logger.warning("token_missing_kid")
            raise credentials_exception
        
        # Fetch the public key
        jwks_client = get_jwks_client()
        key_data = await jwks_client.get_key(kid)
        
        if not key_data:
            logger.warning("token_key_not_found", kid=kid)
            raise credentials_exception
        
        # Construct the public key
        public_key = jwk.construct(key_data)
        
        # Verify and decode the token
        payload_dict = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            options={
                "verify_aud": False,  # Keycloak may not set aud consistently
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        
        return TokenPayload(**payload_dict)
        
    except JWTError as e:
        logger.warning("token_jwt_error", error=str(e))
        raise credentials_exception
    except JWKError as e:
        logger.warning("token_jwk_error", error=str(e))
        raise credentials_exception
    except Exception as e:
        logger.error("token_verification_error", error=str(e))
        raise credentials_exception



# =============================================================================
# Role & Permission Definitions
# =============================================================================

class Permissions:
    """System permissions constants."""
    # User Management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Infant/Mother Management
    PATIENT_READ = "patient:read"
    PATIENT_WRITE = "patient:write"
    PATIENT_ADMIT = "patient:admit"
    PATIENT_DISCHARGE = "patient:discharge"
    
    # Security/Gates
    GATE_READ = "gate:read"
    GATE_CONTROL = "gate:control"
    ZONE_READ = "zone:read"
    ZONE_WRITE = "zone:write"
    
    # RTLS
    RTLS_READ = "rtls:read"
    RTLS_HISTORY = "rtls:history"
    
    # Audit/System
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIG = "system:config"


# Role to Permission Mapping
ROLE_PERMISSIONS = {
    "admin": [
        # Admin has almost everything
        Permissions.USER_READ, Permissions.USER_WRITE, Permissions.USER_DELETE,
        Permissions.PATIENT_READ, Permissions.PATIENT_WRITE, Permissions.PATIENT_ADMIT, Permissions.PATIENT_DISCHARGE,
        Permissions.GATE_READ, Permissions.GATE_CONTROL,
        Permissions.ZONE_READ, Permissions.ZONE_WRITE,
        Permissions.RTLS_READ, Permissions.RTLS_HISTORY,
        Permissions.AUDIT_READ, Permissions.SYSTEM_CONFIG
    ],
    "nurse": [
        # Nurse focuses on patients and monitoring
        Permissions.PATIENT_READ, Permissions.PATIENT_WRITE, Permissions.PATIENT_ADMIT, Permissions.PATIENT_DISCHARGE,
        Permissions.GATE_READ, # Can see if gates are open/closed
        Permissions.RTLS_READ, Permissions.RTLS_HISTORY, # Can track patients
        Permissions.USER_READ, # Can search for other staff
    ],
    "security": [
        # Security focuses on structure and tracking
        Permissions.GATE_READ, Permissions.GATE_CONTROL,
        Permissions.ZONE_READ,
        Permissions.RTLS_READ, Permissions.RTLS_HISTORY,
        Permissions.PATIENT_READ, # Need to identify people
        Permissions.AUDIT_READ, # review logs
    ],
    "viewer": [
        # Read-only basics
        Permissions.PATIENT_READ,
        Permissions.RTLS_READ,
        Permissions.GATE_READ,
    ]
}

def get_permissions_for_roles(roles: List[str]) -> List[str]:
    """Get unique list of permissions for a set of roles."""
    perms = set()
    for role in roles:
        perms.update(ROLE_PERMISSIONS.get(role, []))
    return list(perms)


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    """
    token = credentials.credentials
    payload = await verify_token(token)
    
    roles = extract_roles(payload)
    
    return CurrentUser(
        id=payload.sub,
        email=payload.email,
        username=payload.preferred_username,
        first_name=payload.given_name,
        last_name=payload.family_name,
        roles=roles,
    )


def require_roles(required_roles: List[str], require_all: bool = False):
    """
    Create a dependency that requires specific roles.
    """
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
                user_id=user.id,
                required_roles=required_roles,
                user_roles=user.roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions (Role)",
            )
        
        return user
    
    return role_checker


def require_permission(permission: str):
    """
    Create a dependency that requires a specific granular permission.
    
    Resolves user roles to permissions and checks for the required one.
    """
    async def permission_checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        user_permissions = get_permissions_for_roles(user.roles)
        
        if permission not in user_permissions:
            logger.warning(
                "access_denied_permission",
                user_id=user.id,
                required_permission=permission,
                user_roles=user.roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission}",
            )
        return user
        
    return permission_checker


# Pre-configured role dependencies for common use cases
require_admin = require_roles(["admin"])
require_user_or_admin = require_roles(["user", "admin"])
require_audit_read = require_permission(Permissions.AUDIT_READ)


# Optional authentication - allows unauthenticated access but provides user if authenticated
bearer_scheme_optional = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme_optional),
) -> Optional[CurrentUser]:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for endpoints that behave differently based on authentication status.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

