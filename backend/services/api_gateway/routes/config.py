"""
System Configuration Management API.

Provides endpoints for reading and updating dynamic system settings.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import ConfigType, SystemConfig
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================


class ConfigResponse(BaseModel):
    """Response model for a configuration item."""

    key: str
    value: Any
    type: str
    description: str | None
    is_public: bool
    updated_at: datetime
    updated_by: UUID | None

    class Config:
        from_attributes = True

    @validator("value", pre=True)
    @classmethod
    def parse_value(cls, v, values):
        """Parse value based on type if it's a string."""
        if not isinstance(v, str):
            return v

        # values.data.get("type") if hasattr(values, "data") else None
        # Note: In a real Pydantic validator context, accessing other fields is tricky
        # simpler to return string and let frontend handle parsing or do it in the endpoint
        return v


class ConfigUpdate(BaseModel):
    """Request model for updating a configuration."""

    value: Any
    description: str | None = None


class ConfigCreate(ConfigUpdate):
    """Request model for creating a configuration key."""

    key: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(string|integer|float|boolean|json)$")
    is_public: bool = False


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/config", response_model=list[ConfigResponse])
async def list_config(
    public_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: (
        CurrentUser | None
    ) = None,  # Allow unauthenticated if public_only is True
) -> list[ConfigResponse]:
    """List system configurations."""
    if not public_only and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for internal config",
        )

    query = select(SystemConfig).order_by(SystemConfig.key)

    if public_only:
        query = query.where(SystemConfig.is_public.is_(True))

    result = await db.execute(query)
    configs = result.scalars().all()

    response = []
    for cfg in configs:
        val = cfg.value
        # Type casting logic
        if cfg.type == ConfigType.INTEGER:
            try:
                val = int(val)
            except Exception:
                pass
        elif cfg.type == ConfigType.FLOAT:
            try:
                val = float(val)
            except Exception:
                pass
        elif cfg.type == ConfigType.BOOLEAN:
            val = val.lower() == "true"

        response.append(
            ConfigResponse(
                key=cfg.key,
                value=val,
                type=cfg.type.value,
                description=cfg.description,
                is_public=cfg.is_public,
                updated_at=cfg.updated_at,
                updated_by=cfg.updated_by,
            )
        )

    return response


@router.get("/config/{key}", response_model=ConfigResponse)
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> ConfigResponse:
    """Get a specific configuration value."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found",
        )

    val = config.value
    if config.type == ConfigType.INTEGER:
        try:
            val = int(val)
        except Exception:
            pass
    elif config.type == ConfigType.FLOAT:
        try:
            val = float(val)
        except Exception:
            pass
    elif config.type == ConfigType.BOOLEAN:
        val = val.lower() == "true"

    return ConfigResponse(
        key=config.key,
        value=val,
        type=config.type.value,
        description=config.description,
        is_public=config.is_public,
        updated_at=config.updated_at,
        updated_by=config.updated_by,
    )


@router.put("/config/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    config_data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> ConfigResponse:
    """Update a system configuration value."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found",
        )

    # Update value
    if config_data.value is not None:
        config.value = str(config_data.value)

    if config_data.description is not None:
        config.description = config_data.description

    config.updated_by = current_user.id
    await db.flush()
    await db.commit()

    val = config.value
    if config.type == ConfigType.INTEGER:
        try:
            val = int(val)
        except Exception:
            pass
    elif config.type == ConfigType.FLOAT:
        try:
            val = float(val)
        except Exception:
            pass
    elif config.type == ConfigType.BOOLEAN:
        val = val.lower() == "true"

    return ConfigResponse(
        key=config.key,
        value=val,
        type=config.type.value,
        description=config.description,
        is_public=config.is_public,
        updated_at=config.updated_at,
        updated_by=config.updated_by,
    )


@router.post(
    "/config", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_config(
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> ConfigResponse:
    """Create a new configuration key."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == config_data.key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration key '{config_data.key}' already exists",
        )

    config = SystemConfig(
        key=config_data.key,
        value=str(config_data.value),
        type=ConfigType(config_data.type),
        description=config_data.description,
        is_public=config_data.is_public,
        updated_by=current_user.id,
    )

    db.add(config)
    await db.flush()
    await db.commit()

    val = config.value
    # Simple casting for response
    if config.type == ConfigType.INTEGER:
        try:
            val = int(val)
        except Exception:
            pass
    elif config.type == ConfigType.FLOAT:
        try:
            val = float(val)
        except Exception:
            pass
    elif config.type == ConfigType.BOOLEAN:
        val = val.lower() == "true"

    return ConfigResponse(
        key=config.key,
        value=val,
        type=config.type.value,
        description=config.description,
        is_public=config.is_public,
        updated_at=config.updated_at,
        updated_by=config.updated_by,
    )
