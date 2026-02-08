"""
Biometric enrollment endpoints.

Provides endpoints for infant biometric enrollment and verification.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared_libraries.database import get_db

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class BiometricEnrollRequest(BaseModel):
    """Request model for biometric enrollment."""

    infant_uuid: str
    template_base64: str


class BiometricEnrollResponse(BaseModel):
    """Response model for biometric enrollment."""

    status: str
    infant_uuid: str
    enrolled_at: datetime


class BiometricVerifyRequest(BaseModel):
    """Request model for biometric verification."""

    infant_uuid: str
    template_base64: str


class BiometricVerifyResponse(BaseModel):
    """Response model for biometric verification."""

    verified: bool
    confidence: float
    infant_uuid: str


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/enroll", response_model=BiometricEnrollResponse, status_code=status.HTTP_201_CREATED)
async def enroll_infant(
    request: BiometricEnrollRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll an infant with biometric data.

    In production, this would:
    1. Validate the biometric template format
    2. Store the template securely (encrypted)
    3. Link the template to the infant record

    For simulation, we just acknowledge receipt.
    """
    # In production: Store biometric template reference
    # For simulation: Just return success

    return BiometricEnrollResponse(
        status="enrolled",
        infant_uuid=request.infant_uuid,
        enrolled_at=datetime.utcnow(),
    )


@router.post("/verify", response_model=BiometricVerifyResponse)
async def verify_biometric(
    request: BiometricVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a biometric template against enrolled data.

    In production, this would:
    1. Retrieve the enrolled template for the infant
    2. Perform biometric matching
    3. Return verification result with confidence score

    For simulation, we return success with high confidence.
    """
    # In production: Perform actual biometric matching
    # For simulation: Return success

    return BiometricVerifyResponse(
        verified=True,
        confidence=0.95,
        infant_uuid=request.infant_uuid,
    )
