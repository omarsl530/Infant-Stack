"""
Pytest configuration and async fixtures.
"""
import sys
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# Add project root to sys.path
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from services.api_gateway.main import app
from shared_libraries.database import Base, get_db
from shared_libraries.auth import get_current_user, CurrentUser

# event_loop handled by pytest-asyncio (auto mode)

@pytest.fixture
def mock_admin_user():
    import uuid
    return CurrentUser(
        id=str(uuid.uuid4()),
        email="admin@test.com",
        username="admin",
        first_name="Test",
        last_name="Admin",
        roles=["admin"],
        permissions=["*"]
    )

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def client_with_admin(mock_admin_user) -> AsyncGenerator[AsyncClient, None]:
    """Client with admin auth override."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides = {}
