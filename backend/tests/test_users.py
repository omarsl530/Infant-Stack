import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user_flow(client_with_admin: AsyncClient):
    """
    TC-USER-001: Admin creates valid user via API.
    Verifies that we can create a user and that 422 errors are avoided.
    """
    import uuid

    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "first_name": "Integration",
        "last_name": "Nurse",
        "role": "nurse",
        "password": "securepassword123",  # > 8 chars
    }

    response = await client_with_admin.post("/api/v1/users", json=payload)

    # Debug info if fails
    if response.status_code != 201:
        print(f"Failed with {response.status_code}: {response.text}")

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "nurse"
    assert "id" in data

    # Cleanup/Rollback happens automatically if we used a transaction fixture,
    # but here we rely on the main DB. Ideally we'd delete the user.
    # For now, let's verify fetching the user works too.
    user_id = data["id"]
    get_res = await client_with_admin.get(f"/api/v1/users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == payload["email"]


@pytest.mark.asyncio
async def test_create_user_short_password(client_with_admin: AsyncClient):
    """
    Verify regression logic: short password should return 422.
    """
    payload = {"email": "bad_password@example.com", "role": "nurse", "password": "123"}
    response = await client_with_admin.post("/api/v1/users", json=payload)
    assert response.status_code == 422
