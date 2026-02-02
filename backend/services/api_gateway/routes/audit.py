"""
Audit Log API routes.

Provides endpoints for viewing system audit logs.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import AuditLog
from shared_libraries.auth import CurrentUser, require_audit_read
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogList(BaseModel):
    """Paginated list of audit logs."""

    items: list[AuditLogResponse]
    total: int
    page: int
    limit: int


class AuditFilters(BaseModel):
    """Available filters for audit logs."""

    actions: list[str]
    resource_types: list[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=AuditLogList)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_audit_read),
):
    """
    List audit logs with filtering and pagination.

    Requires 'audit:read' permission.
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_query = select(func.count()).select_from(AuditLog)

    # Apply filters
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)

    if from_time:
        query = query.where(AuditLog.created_at >= from_time)
        count_query = count_query.where(AuditLog.created_at >= from_time)

    if to_time:
        query = query.where(AuditLog.created_at <= to_time)
        count_query = count_query.where(AuditLog.created_at <= to_time)

    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogList(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/filters", response_model=AuditFilters)
async def get_audit_filters(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_audit_read),
):
    """
    Get available filter values (unique actions and resource types).
    """
    # Get unique actions
    action_result = await db.execute(select(AuditLog.action).distinct())
    actions = list(action_result.scalars().all())

    # Get unique resource types
    resource_result = await db.execute(select(AuditLog.resource_type).distinct())
    resource_types = list(resource_result.scalars().all())

    return AuditFilters(
        actions=sorted(actions),
        resource_types=sorted(resource_types),
    )
