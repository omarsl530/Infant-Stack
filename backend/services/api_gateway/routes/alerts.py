"""
Alert management endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Alert
from shared_libraries.auth import CurrentUser, require_roles, require_user_or_admin
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

    model_config = ConfigDict(from_attributes=True)


class AlertList(BaseModel):
    """List of alerts."""

    items: list[AlertResponse]
    total: int


class AlarmStatusResponse(BaseModel):
    """Response model for alarm status polling."""

    alarm_active: bool
    source: str | None = None
    alert_count: int = 0


@router.get("/status", response_model=AlarmStatusResponse)
async def get_alarm_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current alarm status for alarm nodes.

    Returns alarm_active=True if there are any unacknowledged CRITICAL alerts.
    This endpoint is polled by alarm/siren nodes to determine if they should activate.
    """
    from database.orm_models.models import AlertSeverity

    # Query for unacknowledged CRITICAL alerts
    result = await db.execute(
        select(Alert)
        .where(Alert.acknowledged == False)
        .where(Alert.severity == AlertSeverity.CRITICAL)
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    critical_alert = result.scalar_one_or_none()

    # Count all unacknowledged alerts
    count_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.acknowledged == False)
    )
    alert_count = count_result.scalar() or 0

    if critical_alert:
        return AlarmStatusResponse(
            alarm_active=True,
            source=f"{critical_alert.tag_id}_{critical_alert.alert_type}" if critical_alert.tag_id else critical_alert.alert_type,
            alert_count=alert_count,
        )

    return AlarmStatusResponse(
        alarm_active=False,
        source=None,
        alert_count=alert_count,
    )


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
    current_user: CurrentUser = Depends(require_roles(["admin", "security", "nurse"])),
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
    current_user: CurrentUser = Depends(require_roles(["admin", "security", "nurse"])),
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
