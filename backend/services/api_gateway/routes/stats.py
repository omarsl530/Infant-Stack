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

    # User stats - Count ALL users per user request
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    # Active sessions (approximate using last_login in the last 24 hours)
    from datetime import datetime, timedelta

    one_day_ago = datetime.utcnow() - timedelta(hours=24)
    active_sessions_result = await db.execute(
        select(func.count(User.id)).where(User.last_login >= one_day_ago)
    )
    active_sessions = active_sessions_result.scalar() or 0

    # New users this month
    today = datetime.utcnow()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= start_of_month)
    )
    new_users_this_month = new_users_result.scalar() or 0

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
            "active_sessions": active_sessions,
            "new_this_month": new_users_this_month,
        },
        "tags": {
            "total_active": total_active_tags,
            "infants": active_infants,
            "mothers": active_mothers,
        },
        "alerts": {"today": alerts_today, "unacknowledged": unack_alerts},
    }
