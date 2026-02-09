import asyncio
import os
import sys
import json
import base64

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Set env vars manually for debugging if not set
os.environ.setdefault("KEYCLOAK_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "infant-stack")
os.environ.setdefault("KEYCLOAK_ADMIN_CLIENT_ID", "infant-stack-admin")
os.environ.setdefault("KEYCLOAK_ADMIN_CLIENT_SECRET", "admin-client-secret-change-in-production")

from shared_libraries.keycloak_admin import KeycloakAdminClient

def decode_jwt(token):
    parts = token.split('.')
    if len(parts) != 3:
        return "Invalid Token"
    padding = '=' * (4 - len(parts[1]) % 4)
    payload = base64.urlsafe_b64decode(parts[1] + padding).decode('utf-8')
    return json.loads(payload)

async def main():
    print("Initializing Keycloak Admin Client...")
    kc = KeycloakAdminClient()
    
    try:
        print("Attempting to get admin token...")
        token = await kc._get_admin_token()
        print(f"Token obtained!")
        
        # Decode token
        payload = decode_jwt(token)
        print("\n=== Token Payload (Roles) ===")
        print(json.dumps(payload.get('realm_access', {}), indent=2))
        print(json.dumps(payload.get('resource_access', {}), indent=2))
        print("=============================\n")
        
    except Exception as e:
        print(f"Failed to get token: {e}")
        return

    # Try to create a user
    username = f"debug_user_{int(asyncio.get_event_loop().time())}"
    email = f"{username}@example.com"
    print(f"Attempting to create user: {username}")
    
    user_id = await kc.create_user(
        username=username,
        email=email,
        password="password123",
        first_name="Debug",
        last_name="User",
        roles=["nurse"]
    )
    
    if user_id:
        print(f"User created successfully! ID: {user_id}")
        await kc.delete_user(user_id)
    else:
        print("User creation failed!")

if __name__ == "__main__":
    asyncio.run(main())
