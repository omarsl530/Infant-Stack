"""
Gate management endpoints.

Provides CRUD operations for security gates and gate events.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import (
    Gate,
    GateEvent,
    GateState,
)
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class GateResponse(BaseModel):
    """Response model for gate data."""

    id: UUID
    gate_id: str
    name: str
    floor: str
    zone: str
    state: str
    last_state_change: datetime
    camera_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GateList(BaseModel):
    """List of gates."""

    items: list[GateResponse]
    total: int


class GateCreate(BaseModel):
    """Request model for creating a gate."""

    gate_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    floor: str = Field(..., min_length=1, max_length=20)
    zone: str = Field(..., min_length=1, max_length=50)
    camera_id: str | None = None


class GateUpdate(BaseModel):
    """Request model for updating a gate."""

    name: str | None = Field(None, min_length=1, max_length=100)
    zone: str | None = Field(None, min_length=1, max_length=50)
    state: str | None = None
    camera_id: str | None = None


class GateEventResponse(BaseModel):
    """Response model for gate event data."""

    id: UUID
    gate_id: str
    event_type: str
    state: str | None = None
    previous_state: str | None = None
    badge_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    result: str | None = None
    direction: str | None = None
    duration_ms: int | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class GateEventList(BaseModel):
    """List of gate events."""

    items: list[GateEventResponse]
    total: int
    has_more: bool


# =============================================================================
# Gate CRUD Endpoints
# =============================================================================


@router.get("/", response_model=GateList)
async def list_gates(
    floor: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> GateList:
    """List all gates with optional filtering."""
    query = select(Gate).order_by(Gate.floor, Gate.name)

    if floor:
        query = query.where(Gate.floor == floor)
    if state:
        query = query.where(Gate.state == state)

    result = await db.execute(query)
    gates = result.scalars().all()

    count_result = await db.execute(select(func.count(Gate.id)))
    total = count_result.scalar() or 0

    items = [
        GateResponse(
            id=g.id,
            gate_id=g.gate_id,
            name=g.name,
            floor=g.floor,
            zone=g.zone,
            state=g.state.value,
            last_state_change=g.last_state_change,
            camera_id=g.camera_id,
            created_at=g.created_at,
        )
        for g in gates
    ]

    return GateList(items=items, total=total)


@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(
    gate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> GateResponse:
    """Get a specific gate by gate_id."""
    result = await db.execute(select(Gate).where(Gate.gate_id == gate_id))
    gate = result.scalar_one_or_none()

    if not gate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gate {gate_id} not found",
        )

    return GateResponse(
        id=gate.id,
        gate_id=gate.gate_id,
        name=gate.name,
        floor=gate.floor,
        zone=gate.zone,
        state=gate.state.value,
        last_state_change=gate.last_state_change,
        camera_id=gate.camera_id,
        created_at=gate.created_at,
    )


@router.post("/", response_model=GateResponse, status_code=status.HTTP_201_CREATED)
async def create_gate(
    gate_data: GateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> GateResponse:
    """Create a new gate."""
    # Check if gate_id already exists
    existing = await db.execute(select(Gate).where(Gate.gate_id == gate_data.gate_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gate with ID {gate_data.gate_id} already exists",
        )

    gate = Gate(
        gate_id=gate_data.gate_id,
        name=gate_data.name,
        floor=gate_data.floor,
        zone=gate_data.zone,
        camera_id=gate_data.camera_id,
    )
    db.add(gate)
    await db.flush()

    return GateResponse(
        id=gate.id,
        gate_id=gate.gate_id,
        name=gate.name,
        floor=gate.floor,
        zone=gate.zone,
        state=gate.state.value,
        last_state_change=gate.last_state_change,
        camera_id=gate.camera_id,
        created_at=gate.created_at,
    )


@router.patch("/{gate_id}", response_model=GateResponse)
async def update_gate(
    gate_id: str,
    gate_data: GateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> GateResponse:
    """Update a gate."""
    result = await db.execute(select(Gate).where(Gate.gate_id == gate_id))
    gate = result.scalar_one_or_none()

    if not gate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gate {gate_id} not found",
        )

    if gate_data.name is not None:
        gate.name = gate_data.name
    if gate_data.zone is not None:
        gate.zone = gate_data.zone
    if gate_data.camera_id is not None:
        gate.camera_id = gate_data.camera_id
    if gate_data.state is not None:
        gate.state = GateState(gate_data.state)
        gate.last_state_change = datetime.utcnow()

    await db.flush()

    return GateResponse(
        id=gate.id,
        gate_id=gate.gate_id,
        name=gate.name,
        floor=gate.floor,
        zone=gate.zone,
        state=gate.state.value,
        last_state_change=gate.last_state_change,
        camera_id=gate.camera_id,
        created_at=gate.created_at,
    )


@router.delete("/{gate_id}")
async def delete_gate(
    gate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Delete a gate."""
    result = await db.execute(select(Gate).where(Gate.gate_id == gate_id))
    gate = result.scalar_one_or_none()

    if not gate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gate {gate_id} not found",
        )

    await db.delete(gate)

    return {"status": "deleted", "gate_id": gate_id}


# =============================================================================
# Gate Events Endpoints
# =============================================================================


@router.get("/{gate_id}/events", response_model=GateEventList)
async def get_gate_events(
    gate_id: str,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> GateEventList:
    """Get events for a specific gate."""
    query = select(GateEvent).where(GateEvent.gate_id == gate_id)

    if from_time:
        query = query.where(GateEvent.timestamp >= from_time)
    if to_time:
        query = query.where(GateEvent.timestamp <= to_time)
    if event_type:
        query = query.where(GateEvent.event_type == event_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(GateEvent.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    items = [
        GateEventResponse(
            id=e.id,
            gate_id=e.gate_id,
            event_type=e.event_type.value,
            state=e.state.value if e.state else None,
            previous_state=e.previous_state.value if e.previous_state else None,
            badge_id=e.badge_id,
            user_id=e.user_id,
            user_name=e.user_name,
            result=e.result.value if e.result else None,
            direction=e.direction,
            duration_ms=e.duration_ms,
            timestamp=e.timestamp,
        )
        for e in events
    ]

    return GateEventList(items=items, total=total, has_more=offset + len(items) < total)


@router.get("/events/latest", response_model=GateEventList)
async def get_latest_events(
    limit: int = Query(50, ge=1, le=100),
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> GateEventList:
    """Get the latest gate events across all gates."""
    query = select(GateEvent)

    if event_type:
        query = query.where(GateEvent.event_type == event_type)

    query = query.order_by(GateEvent.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    count_result = await db.execute(select(func.count(GateEvent.id)))
    total = count_result.scalar() or 0

    items = [
        GateEventResponse(
            id=e.id,
            gate_id=e.gate_id,
            event_type=e.event_type.value,
            state=e.state.value if e.state else None,
            previous_state=e.previous_state.value if e.previous_state else None,
            badge_id=e.badge_id,
            user_id=e.user_id,
            user_name=e.user_name,
            result=e.result.value if e.result else None,
            direction=e.direction,
            duration_ms=e.duration_ms,
            timestamp=e.timestamp,
        )
        for e in events
    ]

    return GateEventList(items=items, total=total, has_more=len(items) < total)
