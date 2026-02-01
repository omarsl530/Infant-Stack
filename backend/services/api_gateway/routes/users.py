"""
User management API routes.

Provides CRUD operations for users, role assignment, and password management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared_libraries.database import get_db
from shared_libraries.logging import get_logger
from shared_libraries.auth import require_admin
from database.orm_models.models import User, Role, AuditLog

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================

class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: Role = Role.VIEWER


class UserCreate(UserBase):
    """User creation request."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    limit: int


class PasswordUpdate(BaseModel):
    """Password update request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RoleAssignment(BaseModel):
    """Role assignment request."""
    role: Role


# =============================================================================
# Helper Functions
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt or similar."""
    # In production, use proper password hashing (bcrypt, argon2, etc.)
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain) == hashed


async def log_audit(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict = None,
):
    """Log an audit event."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    db.add(audit)
    await db.flush()


# =============================================================================
# User CRUD Endpoints
# =============================================================================

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[Role] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """
    List all users with pagination and filtering.
    
    Admin only.
    """
    query = select(User)
    count_query = select(func.count()).select_from(User)
    
    # Apply filters
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    if search:
        search_filter = (
            User.email.ilike(f"%{search}%") |
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new user.
    
    Admin only.
    """
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    
    # Create user
    user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        hashed_password=hash_password(user_data.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # Audit log
    await log_audit(
        db, current_user.id, "create_user", "user", str(user.id),
        {"email": user.email, "role": user.role.value},
    )
    await db.commit()
    
    logger.info("user_created", user_id=str(user.id), email=user.email)
    
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """
    Get a specific user by ID.
    
    Admin only.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a user.
    
    Admin only.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check email uniqueness if changing
    if user_data.email and user_data.email != user.email:
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
    
    # Apply updates
    update_data = user_data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(user, key, value)
        
        await db.flush()
        await db.refresh(user)
        
        # Audit log
        await log_audit(
            db, current_user.id, "update_user", "user", str(user.id),
            {"updated_fields": list(update_data.keys())},
        )
        await db.commit()
        
        logger.info("user_updated", user_id=str(user.id))
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a user (soft delete by deactivating).
    
    Admin only. Cannot delete self.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Soft delete - deactivate
    user.is_active = False
    
    # Audit log
    await log_audit(
        db, current_user.id, "delete_user", "user", str(user.id),
        {"email": user.email},
    )
    await db.commit()
    
    logger.info("user_deleted", user_id=str(user.id))
    
    return None


# =============================================================================
# Role Management
# =============================================================================

@router.put("/{user_id}/role", response_model=UserResponse)
async def assign_role(
    user_id: UUID,
    role_data: RoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Assign a role to a user.
    
    Admin only.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    old_role = user.role
    user.role = role_data.role
    
    # Audit log
    await log_audit(
        db, current_user.id, "assign_role", "user", str(user.id),
        {"old_role": old_role.value, "new_role": role_data.role.value},
    )
    await db.commit()
    await db.refresh(user)
    
    logger.info("role_assigned", user_id=str(user.id), role=role_data.role.value)
    
    return UserResponse.model_validate(user)


# =============================================================================
# Password Management
# =============================================================================

@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Reset a user's password (admin-initiated).
    
    Generates a temporary password and marks account for password change.
    In production, this would send an email with reset link.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Generate temporary password (in production, send reset email)
    temp_password = "TempPass123!"  # Would be randomly generated
    user.hashed_password = hash_password(temp_password)
    
    # Audit log
    await log_audit(
        db, current_user.id, "reset_password", "user", str(user.id),
    )
    await db.commit()
    
    logger.info("password_reset", user_id=str(user.id))
    
    # In production, would send email with reset instructions
    return None


# =============================================================================
# Self-Service Endpoints
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Should be require_user_or_admin
):
    """Get the current user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Should be require_user_or_admin
):
    """
    Update the current user's profile.
    
    Cannot change own role.
    """
    # Prevent role self-assignment
    if user_data.role and user_data.role != current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role",
        )
    
    # Check email uniqueness
    if user_data.email and user_data.email != current_user.email:
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
    
    # Apply updates (excluding role)
    update_data = user_data.model_dump(exclude_unset=True, exclude={"role", "is_active"})
    if update_data:
        for key, value in update_data.items():
            setattr(current_user, key, value)
        await db.commit()
        await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    password_data: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Should be require_user_or_admin
):
    """Change the current user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    
    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    
    # Audit log
    await log_audit(
        db, current_user.id, "change_password", "user", str(current_user.id),
    )
    await db.commit()
    
    logger.info("password_changed", user_id=str(current_user.id))
    
    return None
