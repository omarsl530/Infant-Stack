"""
RTLS (Real-Time Location System) endpoints.

Provides endpoints for RTLS position tracking and historical data.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import RTLSPosition
from services.api_gateway.routes.websocket import (
    broadcast_alert,
    broadcast_position_update,
    serialize_alert,
)
from services.geofence_service import check_geofence
from shared_libraries.auth import CurrentUser, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class RTLSPositionCreate(BaseModel):
    """Request model for creating a position update."""

    tag_id: str
    asset_type: str
    x: float
    y: float
    z: float = 0.0
    floor: str
    accuracy: float = 0.5
    battery_pct: int = 100
    gateway_id: str | None = None
    rssi: int | None = None


class RTLSPositionResponse(BaseModel):
    """Response model for RTLS position data."""

    id: UUID
    tag_id: str
    asset_type: str
    x: float
    y: float
    z: float
    floor: str
    accuracy: float
    battery_pct: int
    gateway_id: str | None = None
    rssi: int | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class RTLSPositionList(BaseModel):
    """List of RTLS positions."""

    positions: list[RTLSPositionResponse]
    total: int


class RTLSPositionHistoryParams(BaseModel):
    """Parameters for position history query."""

    from_time: datetime
    to_time: datetime
    tag_id: str | None = None
    floor: str | None = None


class RTLSLatestPositions(BaseModel):
    """Latest position for each active tag."""

    positions: list[RTLSPositionResponse]
    total: int
    timestamp: datetime


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/positions",
    response_model=RTLSPositionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_position(
    position_data: RTLSPositionCreate,
    db: AsyncSession = Depends(get_db),
    # In production, this should be protected (e.g., API Key or specialized generic user)
    # current_user: CurrentUser = Depends(require_admin),
):
    """
    Ingest a new RTLS position.

    Triggers:
    - Database insertion
    - Geofence checks
    - WebSocket broadcast
    """
    # 1. Create DB Record
    position = RTLSPosition(
        tag_id=position_data.tag_id,
        asset_type=position_data.asset_type,
        x=position_data.x,
        y=position_data.y,
        z=position_data.z,
        floor=position_data.floor,
        accuracy=position_data.accuracy,
        battery_pct=position_data.battery_pct,
        gateway_id=position_data.gateway_id,
        rssi=position_data.rssi,
    )
    db.add(position)

    # 2. Check (and create) Geofence Alerts
    # We await flush to get ID if needed, but for geofence checking we just need data
    alerts = await check_geofence(
        db,
        position_data.tag_id,
        position_data.asset_type,
        position_data.x,
        position_data.y,
        position_data.floor,
    )

    await db.commit()
    await db.refresh(position)

    # 3. Broadcast Position
    await broadcast_position_update(
        {
            "id": str(position.id),
            "tagId": position.tag_id,
            "assetType": position.asset_type,
            "x": position.x,
            "y": position.y,
            "floor": position.floor,
            "timestamp": position.timestamp.isoformat(),
        }
    )

    # 4. Broadcast Alerts
    for alert in alerts:
        await broadcast_alert(serialize_alert(alert))

    return RTLSPositionResponse(
        id=position.id,
        tag_id=position.tag_id,
        asset_type=position.asset_type,
        x=position.x,
        y=position.y,
        z=position.z,
        floor=position.floor,
        accuracy=position.accuracy,
        battery_pct=position.battery_pct,
        gateway_id=position.gateway_id,
        rssi=position.rssi,
        timestamp=position.timestamp,
    )


@router.get("/positions/latest", response_model=RTLSLatestPositions)
async def get_latest_positions(
    floor: str | None = None,
    asset_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> RTLSLatestPositions:
    """
    Get the latest position for each active tag.

    This uses a subquery to find the most recent position for each tag.
    """
    # Subquery to get max timestamp per tag
    latest_subquery = (
        select(RTLSPosition.tag_id, func.max(RTLSPosition.timestamp).label("max_ts"))
        .group_by(RTLSPosition.tag_id)
        .subquery()
    )

    # Main query joining with the latest positions
    query = select(RTLSPosition).join(
        latest_subquery,
        and_(
            RTLSPosition.tag_id == latest_subquery.c.tag_id,
            RTLSPosition.timestamp == latest_subquery.c.max_ts,
        ),
    )

    if floor:
        query = query.where(RTLSPosition.floor == floor)
    if asset_type:
        query = query.where(RTLSPosition.asset_type == asset_type)

    result = await db.execute(query)
    positions = result.scalars().all()

    items = [
        RTLSPositionResponse(
            id=p.id,
            tag_id=p.tag_id,
            asset_type=p.asset_type,
            x=p.x,
            y=p.y,
            z=p.z,
            floor=p.floor,
            accuracy=p.accuracy,
            battery_pct=p.battery_pct,
            gateway_id=p.gateway_id,
            rssi=p.rssi,
            timestamp=p.timestamp,
        )
        for p in positions
    ]

    return RTLSLatestPositions(
        positions=items,
        total=len(items),
        timestamp=datetime.utcnow(),
    )



from fastapi.responses import StreamingResponse


@router.get("/positions/history", response_model=RTLSPositionList)
async def get_position_history(
    from_time: datetime,
    to_time: datetime,
    tag_id: str | None = None,
    floor: str | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> RTLSPositionList:
    """
    Get historical RTLS positions for a given time range.

    Optionally filter by tag_id and/or floor.
    """
    # Base conditions
    conditions = [
        RTLSPosition.timestamp >= from_time,
        RTLSPosition.timestamp <= to_time,
    ]
    if tag_id:
        conditions.append(RTLSPosition.tag_id == tag_id)
    if floor:
        conditions.append(RTLSPosition.floor == floor)

    combined_filter = and_(*conditions)

    # Get total count (direct count query, more efficient)
    count_query = select(func.count()).select_from(RTLSPosition).where(combined_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get Data
    query = (
        select(RTLSPosition)
        .where(combined_filter)
        .order_by(RTLSPosition.timestamp.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    positions = result.scalars().all()

    items = [
        RTLSPositionResponse(
            id=p.id,
            tag_id=p.tag_id,
            asset_type=p.asset_type,
            x=p.x,
            y=p.y,
            z=p.z,
            floor=p.floor,
            accuracy=p.accuracy,
            battery_pct=p.battery_pct,
            gateway_id=p.gateway_id,
            rssi=p.rssi,
            timestamp=p.timestamp,
        )
        for p in positions
    ]

    return RTLSPositionList(positions=items, total=total)


@router.get("/positions/export", response_class=StreamingResponse)
async def get_position_export(
    from_time: datetime,
    to_time: datetime,
    tag_id: str | None = None,
    floor: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
):
    """
    Export historical RTLS positions as CSV.
    Streamed response to handle large datasets.
    """
    conditions = [
        RTLSPosition.timestamp >= from_time,
        RTLSPosition.timestamp <= to_time,
    ]
    if tag_id:
        conditions.append(RTLSPosition.tag_id == tag_id)
    if floor:
        conditions.append(RTLSPosition.floor == floor)

    async def iter_csv():
        # Header
        yield "timestamp,tag_id,asset_type,floor,x,y,z,accuracy,battery_pct\n"

        # Query in chunks to avoid memory overload
        stmt = (
            select(RTLSPosition)
            .where(and_(*conditions))
            .order_by(RTLSPosition.timestamp.asc())
            .execution_options(yield_per=1000)  # Stream from DB
        )

        result = await db.stream(stmt)

        async for row in result:
            p = row.RTLSPosition
            # Format CSV line
            yield f"{p.timestamp.isoformat()},{p.tag_id},{p.asset_type},{p.floor},{p.x},{p.y},{p.z},{p.accuracy},{p.battery_pct}\n"

    filename = f"rtls_export_{from_time.strftime('%Y%m%d%H%M')}_{to_time.strftime('%Y%m%d%H%M')}.csv"

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/tags/{tag_id}/positions", response_model=RTLSPositionList)
async def get_tag_positions(
    tag_id: str,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> RTLSPositionList:
    """
    Get position history for a specific tag.
    """
    query = select(RTLSPosition).where(RTLSPosition.tag_id == tag_id)

    if from_time:
        query = query.where(RTLSPosition.timestamp >= from_time)
    if to_time:
        query = query.where(RTLSPosition.timestamp <= to_time)

    query = query.order_by(RTLSPosition.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    positions = result.scalars().all()

    items = [
        RTLSPositionResponse(
            id=p.id,
            tag_id=p.tag_id,
            asset_type=p.asset_type,
            x=p.x,
            y=p.y,
            z=p.z,
            floor=p.floor,
            accuracy=p.accuracy,
            battery_pct=p.battery_pct,
            gateway_id=p.gateway_id,
            rssi=p.rssi,
            timestamp=p.timestamp,
        )
        for p in positions
    ]

    return RTLSPositionList(positions=items, total=len(items))


@router.get("/tags/{tag_id}/latest", response_model=RTLSPositionResponse)
async def get_tag_latest_position(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> RTLSPositionResponse:
    """
    Get the latest position for a specific tag.
    """
    result = await db.execute(
        select(RTLSPosition)
        .where(RTLSPosition.tag_id == tag_id)
        .order_by(RTLSPosition.timestamp.desc())
        .limit(1)
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No positions found for tag {tag_id}",
        )

    return RTLSPositionResponse(
        id=position.id,
        tag_id=position.tag_id,
        asset_type=position.asset_type,
        x=position.x,
        y=position.y,
        z=position.z,
        floor=position.floor,
        accuracy=position.accuracy,
        battery_pct=position.battery_pct,
        gateway_id=position.gateway_id,
        rssi=position.rssi,
        timestamp=position.timestamp,
    )
