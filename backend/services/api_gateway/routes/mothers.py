"""
Mother/Guardian management endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Mother, TagStatus
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


class MotherCreate(BaseModel):
    """Request model for creating a mother record."""

    tag_id: str
    name: str  # Combined name for simplicity
    room: str | None = None
    contact_number: str | None = None


class MotherResponse(BaseModel):
    """Response model for mother data."""

    id: UUID
    tag_id: str
    name: str
    room: str | None
    contact_number: str | None
    tag_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MotherList(BaseModel):
    """Paginated list of mothers."""

    items: list[MotherResponse]
    total: int


@router.get("/", response_model=MotherList)
async def list_mothers(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> MotherList:
    """List all mothers."""
    # 1. Fetch Mothers
    query = select(Mother)
    print(f"DEBUG SQL: {query}")
    result = await db.execute(query)
    mothers = result.unique().scalars().all()

    count_result = await db.execute(select(func.count(Mother.id)))
    total = count_result.scalar() or 0

    items = [
        MotherResponse(
            id=m.id,
            tag_id=m.tag_id,
            name=f"{m.first_name} {m.last_name}",
            room=m.room,
            contact_number=m.phone_number,
            tag_status=m.tag_status.value,
            created_at=m.created_at,
        )
        for m in mothers
    ]

    return MotherList(items=items, total=total)


@router.post("/", response_model=MotherResponse, status_code=status.HTTP_201_CREATED)
async def create_mother(
    mother_data: MotherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> MotherResponse:
    """Register a new mother with tag."""
    # Split name into first/last
    name_parts = mother_data.name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Generate MRN
    mrn = f"MRN-{mother_data.tag_id}"

    mother = Mother(
        tag_id=mother_data.tag_id,
        medical_record_number=mrn,
        first_name=first_name,
        last_name=last_name,
        phone_number=mother_data.contact_number,
        ward="Maternity",  # Default ward
        room=mother_data.room,
        tag_status=TagStatus.ACTIVE,
    )

    try:
        db.add(mother)
        await db.flush()
        # Replace db.refresh with explicit select to avoid MissingGreenlet
        result = await db.execute(select(Mother).where(Mother.id == mother.id))
        mother = result.unique().scalar_one()
    except IntegrityError:
        # Check for duplicate key violation
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mother with tag ID {mother_data.tag_id} or MRN already exists",
        ) from None

    return MotherResponse(
        id=mother.id,
        tag_id=mother.tag_id,
        name=f"{mother.first_name} {mother.last_name}",
        room=mother.room,
        contact_number=mother.phone_number,
        tag_status=mother.tag_status.value,
        created_at=mother.created_at,
    )


@router.get("/{mother_id}", response_model=MotherResponse)
async def get_mother(
    mother_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> MotherResponse:
    """Get mother by ID."""
    result = await db.execute(select(Mother).where(Mother.id == mother_id))
    mother = result.unique().scalar_one_or_none()

    if not mother:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother {mother_id} not found",
        )

    return MotherResponse(
        id=mother.id,
        tag_id=mother.tag_id,
        name=f"{mother.first_name} {mother.last_name}",
        room=mother.room,
        contact_number=mother.phone_number,
        tag_status=mother.tag_status.value,
        created_at=mother.created_at,
    )


@router.delete("/{mother_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mother(
    mother_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),  # Admin only
) -> None:
    """Delete a mother and all associated pairings."""
    result = await db.execute(select(Mother).where(Mother.id == mother_id))
    mother = result.unique().scalar_one_or_none()

    if not mother:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother {mother_id} not found",
        )

    # Delete associated pairings via ORM (avoids StaleDataError)
    for pairing in list(mother.pairings):
        await db.delete(pairing)

    # Delete mother
    await db.delete(mother)
    await db.commit()
