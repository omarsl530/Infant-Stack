"""
RTLS (Real-Time Location System) endpoints.

Provides endpoints for RTLS position tracking and historical data.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared_libraries.database import get_db
from shared_libraries.auth import CurrentUser, require_user_or_admin
from database.orm_models.models import RTLSPosition

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

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
    gateway_id: Optional[str] = None
    rssi: Optional[int] = None
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
    tag_id: Optional[str] = None
    floor: Optional[str] = None


class RTLSLatestPositions(BaseModel):
    """Latest position for each active tag."""
    positions: list[RTLSPositionResponse]
    total: int
    timestamp: datetime


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/positions/latest", response_model=RTLSLatestPositions)
async def get_latest_positions(
    floor: Optional[str] = None,
    asset_type: Optional[str] = None,
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
    query = (
        select(RTLSPosition)
        .join(
            latest_subquery,
            and_(
                RTLSPosition.tag_id == latest_subquery.c.tag_id,
                RTLSPosition.timestamp == latest_subquery.c.max_ts,
            ),
        )
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


@router.get("/positions/history", response_model=RTLSPositionList)
async def get_position_history(
    from_time: datetime,
    to_time: datetime,
    tag_id: Optional[str] = None,
    floor: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> RTLSPositionList:
    """
    Get historical RTLS positions for a given time range.
    
    Optionally filter by tag_id and/or floor.
    """
    query = (
        select(RTLSPosition)
        .where(
            and_(
                RTLSPosition.timestamp >= from_time,
                RTLSPosition.timestamp <= to_time,
            )
        )
    )
    
    if tag_id:
        query = query.where(RTLSPosition.tag_id == tag_id)
    if floor:
        query = query.where(RTLSPosition.floor == floor)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(RTLSPosition.timestamp.asc()).offset(offset).limit(limit)
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


@router.get("/tags/{tag_id}/positions", response_model=RTLSPositionList)
async def get_tag_positions(
    tag_id: str,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
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
