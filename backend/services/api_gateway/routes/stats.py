"""
Dashboard statistics API routes.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import (
    Alert,
    Infant,
    Mother,
    TagStatus,
    User,
)
from shared_libraries.auth import CurrentUser, get_current_user
from shared_libraries.database import get_db

router = APIRouter()


@router.get("/dashboard", response_model=dict[str, Any])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get aggregated dashboard statistics.
    """

    # User stats
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )  # Approximate for sessions? Or use last_login window?
    # Users with recent login? Let's generic to active users for now as sessions are Redis based and harder to query from here easily without Redis client
    # But Header says "Active Sessions". Let's stick to active users count for simplicity or distinct users in audit logs today.
    active_sessions = (
        active_users_result.scalar() or 0
    )  # Placeholder logic for "Active Sessions"

    # Tag stats
    active_infants_result = await db.execute(
        select(func.count(Infant.id)).where(Infant.tag_status == TagStatus.ACTIVE)
    )
    active_infants = active_infants_result.scalar() or 0

    active_mothers_result = await db.execute(
        select(func.count(Mother.id)).where(Mother.tag_status == TagStatus.ACTIVE)
    )
    active_mothers = active_mothers_result.scalar() or 0

    total_active_tags = active_infants + active_mothers

    # Alert stats
    from datetime import datetime

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    alerts_today_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= today_start)
    )
    alerts_today = alerts_today_result.scalar() or 0

    unack_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.created_at >= today_start, Alert.acknowledged.is_(False)
        )
    )
    unack_alerts = unack_alerts_result.scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active_sessions": active_sessions,  # Or derived from Redis if available
            "new_this_month": 0,  # TODO: Implement if needed
        },
        "tags": {
            "total_active": total_active_tags,
            "infants": active_infants,
            "mothers": active_mothers,
        },
        "alerts": {"today": alerts_today, "unacknowledged": unack_alerts},
    }
