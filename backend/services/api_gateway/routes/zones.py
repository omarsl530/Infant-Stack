"""
Zone and floorplan management endpoints.

Provides CRUD operations for geofence zones and floorplans.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Floorplan, Zone, ZoneType
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Zone Models
# =============================================================================


class ZoneResponse(BaseModel):
    """Response model for zone data."""

    id: UUID
    name: str
    floor: str
    zone_type: str
    polygon: dict  # List of {x, y} points
    color: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ZoneList(BaseModel):
    """List of zones."""

    items: list[ZoneResponse]
    total: int


class ZoneCreate(BaseModel):
    """Request model for creating a zone."""

    name: str = Field(..., min_length=1, max_length=100)
    floor: str = Field(..., min_length=1, max_length=20)
    zone_type: str = Field(...)  # authorized, restricted, exit
    polygon: dict = Field(...)  # List of {x, y} points
    color: str | None = Field(None, max_length=20)


class ZoneUpdate(BaseModel):
    """Request model for updating a zone."""

    name: str | None = Field(None, min_length=1, max_length=100)
    zone_type: str | None = None
    polygon: dict | None = None
    color: str | None = Field(None, max_length=20)
    is_active: bool | None = None


# =============================================================================
# Floorplan Models
# =============================================================================


class FloorplanResponse(BaseModel):
    """Response model for floorplan data."""

    id: UUID
    floor: str
    name: str
    image_url: str
    width: int
    height: int
    scale: float
    origin_x: float
    origin_y: float
    created_at: datetime

    class Config:
        from_attributes = True


class FloorplanList(BaseModel):
    """List of floorplans."""

    items: list[FloorplanResponse]
    total: int


class FloorplanCreate(BaseModel):
    """Request model for creating a floorplan."""

    floor: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    image_url: str = Field(..., min_length=1, max_length=500)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    scale: float = Field(default=1.0, gt=0)
    origin_x: float = Field(default=0.0)
    origin_y: float = Field(default=0.0)


# =============================================================================
# Zone Endpoints
# =============================================================================


@router.get("/zones", response_model=ZoneList)
async def list_zones(
    floor: str | None = None,
    zone_type: str | None = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> ZoneList:
    """List all zones with optional filtering."""
    query = select(Zone).order_by(Zone.floor, Zone.name)

    if floor:
        query = query.where(Zone.floor == floor)
    if zone_type:
        query = query.where(Zone.zone_type == zone_type)
    if is_active is not None:
        query = query.where(Zone.is_active == is_active)

    result = await db.execute(query)
    zones = result.scalars().all()

    count_result = await db.execute(select(func.count(Zone.id)))
    total = count_result.scalar() or 0

    items = [
        ZoneResponse(
            id=z.id,
            name=z.name,
            floor=z.floor,
            zone_type=z.zone_type.value,
            polygon=z.polygon,
            color=z.color,
            is_active=z.is_active,
            created_at=z.created_at,
            updated_at=z.updated_at,
        )
        for z in zones
    ]

    return ZoneList(items=items, total=total)


@router.get("/zones/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> ZoneResponse:
    """Get a specific zone by ID."""
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        floor=zone.floor,
        zone_type=zone.zone_type.value,
        polygon=zone.polygon,
        color=zone.color,
        is_active=zone.is_active,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.post("/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone_data: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> ZoneResponse:
    """Create a new zone."""
    zone = Zone(
        name=zone_data.name,
        floor=zone_data.floor,
        zone_type=ZoneType(zone_data.zone_type),
        polygon=zone_data.polygon,
        color=zone_data.color,
    )
    db.add(zone)
    await db.flush()

    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        floor=zone.floor,
        zone_type=zone.zone_type.value,
        polygon=zone.polygon,
        color=zone.color,
        is_active=zone.is_active,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.patch("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: UUID,
    zone_data: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> ZoneResponse:
    """Update a zone."""
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    if zone_data.name is not None:
        zone.name = zone_data.name
    if zone_data.zone_type is not None:
        zone.zone_type = ZoneType(zone_data.zone_type)
    if zone_data.polygon is not None:
        zone.polygon = zone_data.polygon
    if zone_data.color is not None:
        zone.color = zone_data.color
    if zone_data.is_active is not None:
        zone.is_active = zone_data.is_active

    await db.flush()

    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        floor=zone.floor,
        zone_type=zone.zone_type.value,
        polygon=zone.polygon,
        color=zone.color,
        is_active=zone.is_active,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.delete("/zones/{zone_id}")
async def delete_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Delete a zone."""
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    await db.delete(zone)

    return {"status": "deleted", "zone_id": str(zone_id)}


# =============================================================================
# Floorplan Endpoints
# =============================================================================


@router.get("/floorplans", response_model=FloorplanList)
async def list_floorplans(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> FloorplanList:
    """List all floorplans."""
    result = await db.execute(select(Floorplan).order_by(Floorplan.floor))
    floorplans = result.scalars().all()

    items = [
        FloorplanResponse(
            id=f.id,
            floor=f.floor,
            name=f.name,
            image_url=f.image_url,
            width=f.width,
            height=f.height,
            scale=f.scale,
            origin_x=f.origin_x,
            origin_y=f.origin_y,
            created_at=f.created_at,
        )
        for f in floorplans
    ]

    return FloorplanList(items=items, total=len(items))


@router.get("/floorplans/{floor}", response_model=FloorplanResponse)
async def get_floorplan(
    floor: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> FloorplanResponse:
    """Get a specific floorplan by floor identifier."""
    result = await db.execute(select(Floorplan).where(Floorplan.floor == floor))
    floorplan = result.scalar_one_or_none()

    if not floorplan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floorplan for floor {floor} not found",
        )

    return FloorplanResponse(
        id=floorplan.id,
        floor=floorplan.floor,
        name=floorplan.name,
        image_url=floorplan.image_url,
        width=floorplan.width,
        height=floorplan.height,
        scale=floorplan.scale,
        origin_x=floorplan.origin_x,
        origin_y=floorplan.origin_y,
        created_at=floorplan.created_at,
    )


@router.post(
    "/floorplans", response_model=FloorplanResponse, status_code=status.HTTP_201_CREATED
)
async def create_floorplan(
    floorplan_data: FloorplanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> FloorplanResponse:
    """Create a new floorplan."""
    existing = await db.execute(
        select(Floorplan).where(Floorplan.floor == floorplan_data.floor)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Floorplan for floor {floorplan_data.floor} already exists",
        )

    floorplan = Floorplan(
        floor=floorplan_data.floor,
        name=floorplan_data.name,
        image_url=floorplan_data.image_url,
        width=floorplan_data.width,
        height=floorplan_data.height,
        scale=floorplan_data.scale,
        origin_x=floorplan_data.origin_x,
        origin_y=floorplan_data.origin_y,
    )
    db.add(floorplan)
    await db.flush()

    return FloorplanResponse(
        id=floorplan.id,
        floor=floorplan.floor,
        name=floorplan.name,
        image_url=floorplan.image_url,
        width=floorplan.width,
        height=floorplan.height,
        scale=floorplan.scale,
        origin_x=floorplan.origin_x,
        origin_y=floorplan.origin_y,
        created_at=floorplan.created_at,
    )


@router.delete("/floorplans/{floor}")
async def delete_floorplan(
    floor: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Delete a floorplan."""
    result = await db.execute(select(Floorplan).where(Floorplan.floor == floor))
    floorplan = result.scalar_one_or_none()

    if not floorplan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floorplan for floor {floor} not found",
        )

    await db.delete(floorplan)

    return {"status": "deleted", "floor": floor}
