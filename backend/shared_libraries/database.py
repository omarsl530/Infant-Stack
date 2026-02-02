"""
Database session management and connection handling.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from database.orm_models.models import Base
from shared_libraries.config import get_settings

settings = get_settings()

# Async engine for API routes (postgres_url already uses asyncpg)
async_engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Sync engine for migrations and scripts
sync_engine = create_engine(
    settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://"),
    echo=settings.debug,
    pool_pre_ping=True,
)

# Session factories
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias for backward compatibility with some services/middleware
session_factory = async_session_factory

sync_session_factory = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes to get a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db() -> Session:
    """Get a synchronous database session for scripts."""
    return sync_session_factory()


async def init_db() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
