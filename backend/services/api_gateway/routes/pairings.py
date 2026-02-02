"""
Pairing endpoints for infant-mother tag management.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Infant, Mother, Pairing, PairingStatus
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================


class PairingCreate(BaseModel):
    """Request model for creating a pairing."""

    infant_id: UUID
    mother_id: UUID


class PairingResponse(BaseModel):
    """Response model for pairing data."""

    id: UUID
    infant_id: UUID
    mother_id: UUID
    infant_tag_id: str
    mother_tag_id: str
    infant_name: str
    mother_name: str
    status: str
    paired_at: datetime
    discharged_at: datetime | None = None

    class Config:
        from_attributes = True


class PairingList(BaseModel):
    """Paginated list of pairings."""

    items: list[PairingResponse]
    total: int
    page: int
    size: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=PairingList)
async def list_pairings(
    status: str | None = "active",
    page: int = 1,
    size: int = 20,
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> PairingList:
    """List all pairings with optional filtering."""
    # TODO: Implement database query
    return PairingList(
        items=[],
        total=0,
        page=page,
        size=size,
    )


@router.post("/", response_model=PairingResponse, status_code=status.HTTP_201_CREATED)
async def create_pairing(
    pairing_data: PairingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> PairingResponse:
    """Create a new infant-mother pairing."""
    # 1. Validate Infant
    result = await db.execute(select(Infant).where(Infant.id == pairing_data.infant_id))
    infant = result.unique().scalar_one_or_none()
    if not infant:
        raise HTTPException(status_code=404, detail="Infant not found")

    # 2. Check for existing active pairing
    existing_pairing = await db.execute(
        select(Pairing)
        .where(Pairing.infant_id == infant.id)
        .where(Pairing.status == PairingStatus.ACTIVE)
    )
    if existing_pairing.scalars().first():
        raise HTTPException(status_code=400, detail="Infant is already paired")

    # 3. Validate Mother
    result = await db.execute(select(Mother).where(Mother.id == pairing_data.mother_id))
    mother = result.unique().scalar_one_or_none()
    if not mother:
        raise HTTPException(status_code=404, detail="Mother not found")

    # 4. Create Pairing
    new_pairing = Pairing(
        infant_id=infant.id,
        mother_id=mother.id,
        status=PairingStatus.ACTIVE,
        paired_at=datetime.utcnow(),
    )

    db.add(new_pairing)
    await db.commit()
    await db.refresh(new_pairing)

    # 5. Return Response (manually construct or use eager load logic if robust)
    # Since we have the objects, we can construct it manually to avoid lazy loads
    return PairingResponse(
        id=new_pairing.id,
        infant_id=infant.id,
        mother_id=mother.id,
        infant_tag_id=infant.tag_id,
        mother_tag_id=mother.tag_id,
        infant_name=f"{infant.first_name} {infant.last_name}",
        mother_name=f"{mother.first_name} {mother.last_name}",
        status=new_pairing.status.value,
        paired_at=new_pairing.paired_at,
        discharged_at=new_pairing.discharged_at,
    )


@router.get("/{pairing_id}", response_model=PairingResponse)
async def get_pairing(
    pairing_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> PairingResponse:
    """Get a specific pairing by ID."""
    result = await db.execute(select(Pairing).where(Pairing.id == pairing_id))
    pairing = result.unique().scalar_one_or_none()

    if not pairing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pairing {pairing_id} not found",
        )

    # Fetch related entities
    infant_result = await db.execute(
        select(Infant).where(Infant.id == pairing.infant_id)
    )
    infant = infant_result.unique().scalar_one()
    mother_result = await db.execute(
        select(Mother).where(Mother.id == pairing.mother_id)
    )
    mother = mother_result.unique().scalar_one()

    return PairingResponse(
        id=pairing.id,
        infant_id=pairing.infant_id,
        mother_id=pairing.mother_id,
        infant_tag_id=infant.tag_id,
        mother_tag_id=mother.tag_id,
        infant_name=f"{infant.first_name} {infant.last_name}",
        mother_name=f"{mother.first_name} {mother.last_name}",
        status=pairing.status.value,
        paired_at=pairing.paired_at,
        discharged_at=pairing.discharged_at,
    )


@router.delete("/{pairing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pairing(
    pairing_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),  # Admin only
) -> None:
    """Delete a pairing (unpair infant from mother)."""
    result = await db.execute(select(Pairing).where(Pairing.id == pairing_id))
    pairing = result.unique().scalar_one_or_none()

    if not pairing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pairing {pairing_id} not found",
        )

    await db.delete(pairing)
    await db.commit()


@router.post("/{pairing_id}/discharge", response_model=PairingResponse)
async def discharge_pairing(pairing_id: UUID) -> PairingResponse:
    """Discharge a pairing (mark as completed).

    This is called when an infant is discharged from the hospital.
    The pairing remains in the system for audit purposes but
    the tags are no longer linked.
    """
    # TODO: Implement discharge logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Discharge not yet implemented",
    )


@router.get("/by-tag/{tag_id}", response_model=PairingResponse)
async def get_pairing_by_tag(tag_id: str) -> PairingResponse:
    """Get the active pairing for a tag (infant or mother)."""
    # TODO: Implement tag lookup
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No active pairing found for tag {tag_id}",
    )


@router.post("/verify-exit")
async def verify_gate_exit(
    infant_tag_id: str,
    mother_tag_id: str,
    gate_id: str,
) -> dict:
    """Verify if an infant-mother pair can exit through a gate.

    Returns authorization status and triggers appropriate actions:
    - If authorized: logs the exit event
    - If unauthorized: triggers alarm and blocks exit
    """
    # TODO: Implement exit verification
    return {
        "authorized": False,
        "reason": "verification_not_implemented",
        "infant_tag": infant_tag_id,
        "mother_tag": mother_tag_id,
        "gate": gate_id,
    }
