"""
Alert management endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Alert
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


class AlertResponse(BaseModel):
    """Response model for alert data."""

    id: UUID
    alert_type: str
    severity: str
    message: str
    tag_id: str | None
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertList(BaseModel):
    """List of alerts."""

    items: list[AlertResponse]
    total: int


@router.get("/", response_model=AlertList)
async def list_alerts(
    acknowledged: bool | None = False,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> AlertList:
    """List all alerts with optional filtering."""
    query = select(Alert).order_by(Alert.created_at.desc())

    if acknowledged is not None:
        query = query.where(Alert.acknowledged == acknowledged)
    if severity:
        query = query.where(Alert.severity == severity)

    result = await db.execute(query)
    alerts = result.scalars().all()

    count_result = await db.execute(select(func.count(Alert.id)))
    total = count_result.scalar() or 0

    items = [
        AlertResponse(
            id=a.id,
            alert_type=a.alert_type,
            severity=a.severity.value,
            message=a.message,
            tag_id=a.tag_id,
            acknowledged=a.acknowledged,
            created_at=a.created_at,
        )
        for a in alerts
    ]

    return AlertList(items=items, total=total)


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),  # Admin only
) -> dict:
    """Acknowledge an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    await db.flush()

    return {"status": "acknowledged", "alert_id": str(alert_id)}


@router.delete("/{alert_id}")
async def dismiss_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),  # Admin only
) -> dict:
    """Dismiss (delete) an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    await db.delete(alert)

    return {"status": "dismissed", "alert_id": str(alert_id)}
