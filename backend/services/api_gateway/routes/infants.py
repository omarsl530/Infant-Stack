"""
Infant management endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Infant, TagStatus
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()
router = APIRouter()


class InfantCreate(BaseModel):
    """Request model for creating an infant record."""

    tag_id: str
    name: str  # Combined name for simplicity
    ward: str
    room: str | None = None
    date_of_birth: datetime | None = None
    weight: str | None = None


class InfantResponse(BaseModel):
    """Response model for infant data."""

    id: UUID
    tag_id: str
    name: str
    ward: str
    room: str | None
    tag_status: str
    date_of_birth: datetime | None = None
    weight: str | None = None
    created_at: datetime
    # Pairing info
    mother_name: str | None = None
    mother_tag_id: str | None = None

    class Config:
        from_attributes = True


class InfantList(BaseModel):
    """Paginated list of infants."""

    items: list[InfantResponse]
    total: int


@router.get("/", response_model=InfantList)
async def list_infants(
    ward: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> InfantList:
    """List all infants with optional filtering."""
    # 1. Fetch Infants
    query = select(Infant)

    if ward:
        query = query.where(Infant.ward == ward)
    if status:
        query = query.where(Infant.tag_status == status)

    result = await db.execute(query)
    infants = result.unique().scalars().all()

    # Count total (distinct infants)
    count_result = await db.execute(select(func.count(Infant.id)))
    total = count_result.scalar() or 0

    items = []
    for infant in infants:
        # Get active pairing if exists
        mother_name = None
        mother_tag_id = None
        for pairing in infant.pairings:
            if pairing.status.value.lower() == "active":
                mother_name = f"{pairing.mother.first_name} {pairing.mother.last_name}"
                mother_tag_id = pairing.mother.tag_id
                break

        items.append(
            InfantResponse(
                id=infant.id,
                tag_id=infant.tag_id,
                name=f"{infant.first_name} {infant.last_name}",
                ward=infant.ward,
                room=infant.room,
                tag_status=infant.tag_status.value,
                date_of_birth=infant.date_of_birth,
                created_at=infant.created_at,
                mother_name=mother_name,
                mother_tag_id=mother_tag_id,
            )
        )

    return InfantList(items=items, total=total)


@router.post("/", response_model=InfantResponse, status_code=status.HTTP_201_CREATED)
async def create_infant(
    infant_data: InfantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> InfantResponse:
    """Register a new infant with tag."""
    # Split name into first/last
    name_parts = infant_data.name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Generate MRN
    mrn = f"MRN-{infant_data.tag_id}"

    infant = Infant(
        tag_id=infant_data.tag_id,
        medical_record_number=mrn,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=infant_data.date_of_birth or datetime.utcnow(),
        ward=infant_data.ward,
        room=infant_data.room,
        tag_status=TagStatus.ACTIVE,
    )

    try:
        db.add(infant)
        await db.flush()
        await db.refresh(infant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Infant with tag ID {infant_data.tag_id} or MRN already exists",
        ) from None

    return InfantResponse(
        id=infant.id,
        tag_id=infant.tag_id,
        name=f"{infant.first_name} {infant.last_name}",
        ward=infant.ward,
        room=infant.room,
        tag_status=infant.tag_status.value,
        date_of_birth=infant.date_of_birth,
        created_at=infant.created_at,
    )


@router.get("/{infant_id}", response_model=InfantResponse)
async def get_infant(
    infant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> InfantResponse:
    """Get infant by ID."""
    result = await db.execute(select(Infant).where(Infant.id == infant_id))
    infant = result.scalar_one_or_none()

    if not infant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infant {infant_id} not found",
        )

    return InfantResponse(
        id=infant.id,
        tag_id=infant.tag_id,
        name=f"{infant.first_name} {infant.last_name}",
        ward=infant.ward,
        room=infant.room,
        tag_status=infant.tag_status.value,
        date_of_birth=infant.date_of_birth,
        created_at=infant.created_at,
    )


@router.delete("/{infant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_infant(
    infant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),  # Admin only
) -> None:
    """Delete an infant and all associated pairings."""
    # Check infant exists
    result = await db.execute(select(Infant).where(Infant.id == infant_id))
    infant = result.unique().scalar_one_or_none()

    if not infant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infant {infant_id} not found",
        )

    # Delete associated pairings via ORM (avoids StaleDataError)
    for pairing in list(infant.pairings):
        await db.delete(pairing)

    # Delete infant
    await db.delete(infant)
    await db.commit()
