"""
Keycloak Admin REST API Client.

Provides programmatic user management through Keycloak's Admin REST API.
Uses confidential client credentials to obtain admin access tokens.
"""

from typing import Any

import httpx
from pydantic import BaseModel

from shared_libraries.config import get_settings
from shared_libraries.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class KeycloakUser(BaseModel):
    """Keycloak user representation."""

    id: str | None = None
    username: str
    email: str
    firstName: str | None = None
    lastName: str | None = None
    enabled: bool = True
    emailVerified: bool = False
    credentials: list[dict[str, Any]] | None = None
    realmRoles: list[str] | None = None


class KeycloakAdminClient:
    """
    Client for Keycloak Admin REST API.

    Provides methods for creating users and managing role assignments.
    Uses client credentials grant to obtain admin access tokens.
    """

    def __init__(self):
        self.base_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_admin_client_id
        self.client_secret = settings.keycloak_admin_client_secret
        self._access_token: str | None = None

    @property
    def admin_api_url(self) -> str:
        """Admin API base URL for the realm."""
        return f"{self.base_url}/admin/realms/{self.realm}"

    @property
    def token_url(self) -> str:
        """Token endpoint URL."""
        return f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

    async def _get_admin_token(self) -> str:
        """
        Obtain admin access token via client credentials grant.

        Returns:
            Access token string

        Raises:
            Exception: If token acquisition fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(
                    "keycloak_admin_token_failed",
                    status=response.status_code,
                    error=response.text,
                )
                raise Exception(f"Failed to obtain admin token: {response.status_code}")

            token_data = response.json()
            return token_data["access_token"]

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """
        Make authenticated request to Keycloak Admin API.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to admin API base)
            json_data: Optional JSON body
            params: Optional query parameters

        Returns:
            HTTP response
        """
        # Get fresh token for each request (tokens are short-lived)
        token = await self._get_admin_token()

        url = f"{self.admin_api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=10.0,
            )
            return response

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
        roles: list[str] | None = None,
        enabled: bool = True,
        email_verified: bool = True,
        temporary_password: bool = False,
    ) -> str | None:
        """
        Create a new user in Keycloak.

        Args:
            username: User's username
            email: User's email address
            password: Initial password
            first_name: User's first name
            last_name: User's last name
            roles: List of realm role names to assign
            enabled: Whether the user account is enabled
            email_verified: Whether to mark email as verified
            temporary_password: If True, user must change password on first login

        Returns:
            Created user's ID, or None if creation failed
        """
        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
            "emailVerified": email_verified,
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": temporary_password,
                }
            ],
        }

        # Create user
        response = await self._request("POST", "/users", json_data=user_data)

        if response.status_code == 201:
            # Get user ID from Location header
            location = response.headers.get("Location", "")
            user_id = location.split("/")[-1] if location else None

            logger.info("keycloak_user_created", username=username, user_id=user_id)

            # Assign roles if specified
            if roles and user_id:
                await self.assign_roles(user_id, roles)

            return user_id
        elif response.status_code == 409:
            logger.warning("keycloak_user_exists", username=username)
            return None
        else:
            logger.error(
                "keycloak_user_creation_failed",
                username=username,
                status=response.status_code,
                error=response.text,
            )
            return None

    async def get_realm_roles(self) -> list[dict[str, Any]]:
        """
        Get all realm-level roles.

        Returns:
            List of role representations
        """
        response = await self._request("GET", "/roles")

        if response.status_code == 200:
            return response.json()

        logger.error("keycloak_get_roles_failed", status=response.status_code)
        return []

    async def assign_roles(self, user_id: str, role_names: list[str]) -> bool:
        """
        Assign realm roles to a user.

        Args:
            user_id: Keycloak user ID
            role_names: List of role names to assign

        Returns:
            True if successful, False otherwise
        """
        # Get all realm roles
        all_roles = await self.get_realm_roles()

        # Filter to requested roles
        roles_to_assign = [
            {"id": role["id"], "name": role["name"]}
            for role in all_roles
            if role["name"] in role_names
        ]

        if not roles_to_assign:
            logger.warning("keycloak_no_matching_roles", requested=role_names)
            return False

        # Assign roles
        response = await self._request(
            "POST",
            f"/users/{user_id}/role-mappings/realm",
            json_data=roles_to_assign,
        )

        if response.status_code == 204:
            logger.info(
                "keycloak_roles_assigned",
                user_id=user_id,
                roles=role_names,
            )
            return True

        logger.error(
            "keycloak_role_assignment_failed",
            user_id=user_id,
            status=response.status_code,
            error=response.text,
        )
        return False

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """
        Find a user by username.

        Args:
            username: Username to search for

        Returns:
            User representation or None if not found
        """
        response = await self._request(
            "GET",
            "/users",
            params={"username": username, "exact": "true"},
        )

        if response.status_code == 200:
            users = response.json()
            return users[0] if users else None

        return None

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user from Keycloak.

        Args:
            user_id: Keycloak user ID

        Returns:
            True if deleted successfully
        """
        response = await self._request("DELETE", f"/users/{user_id}")

        if response.status_code == 204:
            logger.info("keycloak_user_deleted", user_id=user_id)
            return True

        logger.error(
            "keycloak_user_deletion_failed",
            user_id=user_id,
            status=response.status_code,
        )
        return False


# Singleton instance
_admin_client: KeycloakAdminClient | None = None


def get_keycloak_admin() -> KeycloakAdminClient:
    """Get or create the Keycloak admin client singleton."""
    global _admin_client
    if _admin_client is None:
        _admin_client = KeycloakAdminClient()
    return _admin_client
