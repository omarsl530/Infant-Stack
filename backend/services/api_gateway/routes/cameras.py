"""
Camera management endpoints.

Provides CRUD operations for cameras and snapshot retrieval.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared_libraries.database import get_db
from shared_libraries.auth import CurrentUser, require_admin, require_user_or_admin
from database.orm_models.models import Camera, CameraStatus

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class CameraResponse(BaseModel):
    """Response model for camera data."""
    id: UUID
    camera_id: str
    name: str
    floor: str
    zone: Optional[str] = None
    gate_id: Optional[str] = None
    stream_url: str
    thumbnail_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CameraList(BaseModel):
    """List of cameras."""
    items: list[CameraResponse]
    total: int


class CameraCreate(BaseModel):
    """Request model for creating a camera."""
    camera_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    floor: str = Field(..., min_length=1, max_length=20)
    zone: Optional[str] = Field(None, max_length=50)
    gate_id: Optional[str] = Field(None, max_length=50)
    stream_url: str = Field(..., min_length=1, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)


class CameraUpdate(BaseModel):
    """Request model for updating a camera."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    zone: Optional[str] = Field(None, max_length=50)
    gate_id: Optional[str] = None
    stream_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=CameraList)
async def list_cameras(
    floor: Optional[str] = None,
    status: Optional[str] = None,
    gate_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> CameraList:
    """List all cameras with optional filtering."""
    query = select(Camera).order_by(Camera.floor, Camera.name)
    
    if floor:
        query = query.where(Camera.floor == floor)
    if status:
        query = query.where(Camera.status == status)
    if gate_id:
        query = query.where(Camera.gate_id == gate_id)
    
    result = await db.execute(query)
    cameras = result.scalars().all()
    
    count_result = await db.execute(select(func.count(Camera.id)))
    total = count_result.scalar() or 0
    
    items = [
        CameraResponse(
            id=c.id,
            camera_id=c.camera_id,
            name=c.name,
            floor=c.floor,
            zone=c.zone,
            gate_id=c.gate_id,
            stream_url=c.stream_url,
            thumbnail_url=c.thumbnail_url,
            status=c.status.value,
            created_at=c.created_at,
        )
        for c in cameras
    ]
    
    return CameraList(items=items, total=total)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> CameraResponse:
    """Get a specific camera by camera_id."""
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )
    
    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        floor=camera.floor,
        zone=camera.zone,
        gate_id=camera.gate_id,
        stream_url=camera.stream_url,
        thumbnail_url=camera.thumbnail_url,
        status=camera.status.value,
        created_at=camera.created_at,
    )


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> CameraResponse:
    """Create a new camera."""
    existing = await db.execute(select(Camera).where(Camera.camera_id == camera_data.camera_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Camera with ID {camera_data.camera_id} already exists",
        )
    
    camera = Camera(
        camera_id=camera_data.camera_id,
        name=camera_data.name,
        floor=camera_data.floor,
        zone=camera_data.zone,
        gate_id=camera_data.gate_id,
        stream_url=camera_data.stream_url,
        thumbnail_url=camera_data.thumbnail_url,
    )
    db.add(camera)
    await db.flush()
    
    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        floor=camera.floor,
        zone=camera.zone,
        gate_id=camera.gate_id,
        stream_url=camera.stream_url,
        thumbnail_url=camera.thumbnail_url,
        status=camera.status.value,
        created_at=camera.created_at,
    )


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: str,
    camera_data: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> CameraResponse:
    """Update a camera."""
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )
    
    if camera_data.name is not None:
        camera.name = camera_data.name
    if camera_data.zone is not None:
        camera.zone = camera_data.zone
    if camera_data.gate_id is not None:
        camera.gate_id = camera_data.gate_id
    if camera_data.stream_url is not None:
        camera.stream_url = camera_data.stream_url
    if camera_data.thumbnail_url is not None:
        camera.thumbnail_url = camera_data.thumbnail_url
    if camera_data.status is not None:
        camera.status = CameraStatus(camera_data.status)
    
    await db.flush()
    
    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        floor=camera.floor,
        zone=camera.zone,
        gate_id=camera.gate_id,
        stream_url=camera.stream_url,
        thumbnail_url=camera.thumbnail_url,
        status=camera.status.value,
        created_at=camera.created_at,
    )


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Delete a camera."""
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )
    
    await db.delete(camera)
    
    return {"status": "deleted", "camera_id": camera_id}


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> dict:
    """
    Get the snapshot URL for a camera.
    
    In a full implementation, this would either return a cached thumbnail
    or proxy to the camera's RTSP stream to capture a frame.
    """
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )
    
    # Return thumbnail URL or a placeholder
    return {
        "camera_id": camera_id,
        "snapshot_url": camera.thumbnail_url or f"/api/v1/cameras/{camera_id}/snapshot.jpg",
        "status": camera.status.value,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/{camera_id}/stream")
async def get_camera_stream(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_user_or_admin),
) -> dict:
    """
    Get the stream URL for a camera.
    
    Returns the RTSP or HLS stream URL for the camera.
    """
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )
    
    if camera.status != CameraStatus.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Camera {camera_id} is currently {camera.status.value}",
        )
    
    return {
        "camera_id": camera_id,
        "stream_url": camera.stream_url,
        "status": camera.status.value,
    }
