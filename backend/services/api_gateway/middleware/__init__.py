"""
API Gateway Middleware Package

Provides authentication, audit, and other middleware components.
"""

from .auth import (
    CurrentUser,
    TokenPayload,
    get_current_user,
    get_current_user_optional,
    require_role,
    require_all_roles,
)

__all__ = [
    "CurrentUser",
    "TokenPayload",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_all_roles",
]
