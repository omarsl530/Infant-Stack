"""
Pytest configuration and async fixtures.
"""

import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Add project root to sys.path
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from services.api_gateway.main import app
from shared_libraries.auth import CurrentUser, get_current_user


# event_loop handled by pytest-asyncio (auto mode), but we need session scope for global engine compatibility
@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


from sqlalchemy import select

from database.orm_models.models import User
from shared_libraries.database import async_session_factory, init_db


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Initialize database schema once per test session."""
    await init_db()


@pytest.fixture
async def db_admin_user():
    """Fetch a real admin user from the DB for integration tests."""
    async with async_session_factory() as session:
        from database.orm_models.roles import Role

        # Try to find existing admin
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        user = result.scalars().first()
        if not user:
            # Find admin role
            role_result = await session.execute(
                select(Role).where(Role.name == "admin")
            )
            admin_role = role_result.scalars().first()
            if not admin_role:
                # Seed required roles
                admin_role = Role(
                    name="admin",
                    description="Full system access",
                    permissions=["*"],
                    is_system=True,
                )
                nurse_role = Role(
                    name="nurse",
                    description="Medical staff access",
                    permissions=["infants:read", "infants:write", "mothers:read"],
                    is_system=True,
                )
                session.add(admin_role)
                session.add(nurse_role)
                await session.flush()

            # Create the admin user if missing (Auto-seeding for tests)
            user = User(
                email="admin@example.com",
                hashed_password="hashed_admin_secret",
                first_name="Admin",
                last_name="System",
                role=admin_role,  # Assign OBJECT, not string
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Create a CurrentUser object that matches what the auth middleware expects
        # BUT keeps the ID consistent with the DB for audit logs
        return CurrentUser(
            id=str(user.id),
            email=user.email,
            username="admin",  # keycloak username often matches email or separate, adapting...
            first_name=user.first_name,
            last_name=user.last_name,
            roles=["admin"],
            permissions=["*"],
        )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def client_with_admin(db_admin_user) -> AsyncGenerator[AsyncClient, None]:
    """Client with admin auth override using REAL user ID."""
    app.dependency_overrides[get_current_user] = lambda: db_admin_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides = {}
