import asyncio
import os
import sys
import httpx

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
TARGET_REALM = "infant-stack"
TARGET_CLIENT_ID = "infant-stack-admin"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Get Access Token for Admin in Master Realm
        print(f"Authenticating as {ADMIN_USER} in master realm...")
        resp = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
                "grant_type": "password",
                "client_id": "admin-cli",
            },
        )
        if resp.status_code != 200:
            print(f"Failed to authenticate: {resp.text}")
            return
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully.")

        # 2. Get Client UUID for target client
        print(f"Finding client {TARGET_CLIENT_ID} in realm {TARGET_REALM}...")
        resp = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{TARGET_REALM}/clients",
            params={"clientId": TARGET_CLIENT_ID},
            headers=headers,
        )
        clients = resp.json()
        if not clients:
            print("Target client not found.")
            return
        client_uuid = clients[0]["id"]
        print(f"Found client UUID: {client_uuid}")

        # 3. Get Service Account User for the client
        print("Getting service account user...")
        resp = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{TARGET_REALM}/clients/{client_uuid}/service-account-user",
            headers=headers,
        )
        if resp.status_code != 200:
            print(f"Failed to get service account user: {resp.text}")
            # Ensure service accounts enabled for client
            return
        service_account_user = resp.json()
        user_id = service_account_user["id"]
        print(f"Service Account User ID: {user_id}")

        # 4. Get 'realm-management' client UUID
        print("Finding 'realm-management' client...")
        resp = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{TARGET_REALM}/clients",
            params={"clientId": "realm-management"},
            headers=headers,
        )
        mgmt_clients = resp.json()
        if not mgmt_clients:
            print("'realm-management' client not found.")
            return
        mgmt_client_uuid = mgmt_clients[0]["id"]
        print(f"Found realm-management UUID: {mgmt_client_uuid}")

        # 5. Get 'manage-users' role
        print("Finding 'manage-users' role...")
        resp = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{TARGET_REALM}/clients/{mgmt_client_uuid}/roles/manage-users",
            headers=headers,
        )
        if resp.status_code != 200:
             print(f"Failed to find role: {resp.text}")
             return
        role_data = resp.json()
        print(f"Found role: {role_data['name']}")

        # 6. Assign role to service account
        print("Assigning role to service account...")
        resp = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{TARGET_REALM}/users/{user_id}/role-mappings/clients/{mgmt_client_uuid}",
            json=[role_data],
            headers=headers,
        )
        
        if resp.status_code == 204:
            print("SUCCESS: Role assigned.")
        else:
             print(f"Failed to assign role: {resp.status_code} {resp.text}")

        # Also assign 'view-users' and 'query-users' and 'manage-realm' potentially?
        # Just 'manage-users' is usually enough for creating users.
        # But 'query-users' might be needed for searching.
        
        # Let's also check if 'manage-realm' is needed for roles?
        # For our test we just create user.

if __name__ == "__main__":
    asyncio.run(main())
