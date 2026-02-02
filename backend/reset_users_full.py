
import asyncio
import logging
import httpx
from uuid import UUID

from sqlalchemy import delete, select

from shared_libraries.database import async_session_factory
from database.orm_models.models import User
from database.orm_models.roles import Role
from shared_libraries.keycloak_admin import get_keycloak_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_master_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": "admin",
            },
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        logger.error(f"Failed to get master token: {response.status_code} {response.text}")
        return None

async def fix_permissions():
    """Grant realm-admin role to infant-stack-admin service account."""
    logger.info("Attempting to fix Service Account permissions...")
    token = await get_master_token()
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = "http://localhost:8080/admin/realms/infant-stack"
    async with httpx.AsyncClient() as client:
        # 1. Find Service Account User
        # The username for service account is usually 'service-account-<client_id>'
        sa_username = "service-account-infant-stack-admin"
        resp = await client.get(f"{base_url}/users", params={"username": sa_username}, headers=headers)
        if resp.status_code != 200 or not resp.json():
            logger.error(f"Could not find service account user {sa_username}")
            return False
        sa_user_id = resp.json()[0]["id"]
        logger.info(f"Found Service Account User ID: {sa_user_id}")

        # 2. Find realm-management Client
        resp = await client.get(f"{base_url}/clients", params={"clientId": "realm-management"}, headers=headers)
        if resp.status_code != 200 or not resp.json():
            logger.error("Could not find realm-management client")
            return False
        mgmt_client_id = resp.json()[0]["id"]

        # 3. Find realm-admin Role
        resp = await client.get(f"{base_url}/clients/{mgmt_client_id}/roles/realm-admin", headers=headers)
        if resp.status_code != 200:
            logger.error("Could not find realm-admin role")
            return False
        role_data = resp.json()
        
        # 4. Assign Role
        resp = await client.post(
            f"{base_url}/users/{sa_user_id}/role-mappings/clients/{mgmt_client_id}",
            json=[role_data],
            headers=headers
        )
        if resp.status_code in [204, 201, 200]: # 204 typically
            logger.info("Successfully granted realm-admin to service account!")
            return True
        else:
            logger.error(f"Failed to assign role: {resp.status_code} {resp.text}")
            return False

async def reset_users():
    """
    1. Fix Permissions (using Master Admin).
    2. Delete targeted users from Keycloak.
    3. Delete all users from Postgres.
    4. Re-create admin@infantstack.com and nurse@infantstack.com.
    """
    logger.info("Starting User Reset...")

    # Validate Master Access & Fix Permissions
    if not await fix_permissions():
        logger.warning("Permission fix failed. Proceeding with standard client, which may fail if 403 previously occurred.")

    # Initialize Keycloak Client (Now hopefully empowered)
    kc_admin = get_keycloak_admin()
    
    # --- 1. Wipe Keycloak (Targeted) ---
    logger.info("Attempting to clean up Keycloak users...")
    
    # List of users we definitely want to clear to ensure clean state
    targets = [
        "admin@infantstack.com", 
        "nurse@infantstack.com", 
        "omarsl530@gmail.com", 
        "admin@example.com",
        "empty", 
        "user_uuid" # placeholders
    ]

    for target_email in targets:
        try:
            # Try to find by username/email
            user = await kc_admin.get_user_by_username(target_email)
            if user:
                uid = user['id']
                logger.info(f"Deleting Keycloak user: {target_email} ({uid})")
                await kc_admin.delete_user(uid)
            else:
                logger.info(f"Keycloak user {target_email} not found (clean).")
        except Exception as e:
            logger.warning(f"Failed to check/delete {target_email} in Keycloak: {e}")

    # --- 2. Wipe Postgres ---
    async with async_session_factory() as db:
        logger.info("Cleaning up Postgres dependencies...")
        
        try:
            import sqlalchemy
            from sqlalchemy import text
            
            # Nullify references first to avoid IntegrityErrors
            await db.execute(text("UPDATE audit_logs SET user_id = NULL"))
            await db.execute(text("UPDATE pairings SET paired_by_user_id = NULL"))
            await db.execute(text("UPDATE alerts SET acknowledged_by = NULL"))
            await db.execute(text("UPDATE system_config SET updated_by = NULL"))
            await db.commit()

            logger.info("Wiping Postgres users table...")
            await db.execute(delete(User))
            await db.commit()
            logger.info("Postgres users deleted.")
        except Exception as e:
            logger.error(f"Failed to wipe Postgres users: {e}")
            return

        # Fetch Roles for seeding
        roles_result = await db.execute(select(Role))
        roles = {r.name: r for r in roles_result.scalars().all()}
        
        if "admin" not in roles or "nurse" not in roles:
            logger.error("Missing required roles (admin/nurse) in DB! Run migrations/seeds first.")
            return

        # --- 3. Seed Default Users ---
        default_users = [
            {
                "email": "admin@infantstack.com",
                "password": "password123",
                "first_name": "Admin",
                "last_name": "User",
                "role": "admin"
            },
            {
                "email": "nurse@infantstack.com",
                "password": "password123",
                "first_name": "Nurse",
                "last_name": "User",
                "role": "nurse"
            }
        ]

        logger.info("Seeding default users...")
        for u_data in default_users:
            logger.info(f"Creating {u_data['email']}...")
            
            # A. Create in Keycloak
            kc_id = await kc_admin.create_user(
                username=u_data["email"],
                email=u_data["email"],
                password=u_data["password"],
                first_name=u_data["first_name"],
                last_name=u_data["last_name"],
                roles=[u_data["role"]],
                enabled=True,
                email_verified=True
            )
            
            if not kc_id:
                logger.error(f"Failed to create {u_data['email']} in Keycloak!")
                continue

            # B. Create in Postgres
            new_user = User(
                id=UUID(kc_id), # Sync ID
                email=u_data["email"],
                first_name=u_data["first_name"],
                last_name=u_data["last_name"],
                role=roles[u_data["role"]],
                hashed_password="OIDC_MANAGED",
                is_active=True
            )
            db.add(new_user)
        
        await db.commit()
        logger.info("Default users seeded successfully in Keycloak and DB.")

if __name__ == "__main__":
    asyncio.run(reset_users())
