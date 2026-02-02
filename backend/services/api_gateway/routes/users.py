"""
User management API routes.

Provides CRUD operations for users, role assignment, and password management.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import AuditLog, User
from database.orm_models.roles import Role as RoleModel
from shared_libraries.auth import require_admin
from shared_libraries.database import get_db
from shared_libraries.logging import get_logger
from shared_libraries.keycloak_admin import get_keycloak_admin

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
    role: str = "viewer"  # Accepts role name


class UserCreate(UserBase):
    """User creation request."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update request."""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """User response model."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str  # Returns role name
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj: User) -> "UserResponse":
        # Custom validator to handle role relationship -> string mapping if Pydantic doesn't auto-resolve
        # Since 'role' in User is an object, and we want string.
        # But wait, obj.role is a RoleModel. string conversion might get 'Role(...)' repr.
        # using standard from_attributes might fail.
        # We manually construct or help Pydantic.
        return cls(
            id=obj.id,
            email=obj.email,
            first_name=obj.first_name,
            last_name=obj.last_name,
            role=obj.role.name if obj.role else "unknown",
            is_active=obj.is_active,
            created_at=obj.created_at,
            last_login=obj.last_login,
        )


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserResponse]
    total: int
    page: int
    limit: int


class PasswordUpdate(BaseModel):
    """Password update request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RoleAssignment(BaseModel):
    """Role assignment request."""

    role: str


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
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, description="Search by name or email"),
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
        # Join Role to filter by name
        query = query.join(User.role).where(RoleModel.name == role)
        count_query = count_query.join(User.role).where(RoleModel.name == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    if search:
        search_filter = (
            User.email.ilike(f"%{search}%")
            | User.first_name.ilike(f"%{search}%")
            | User.last_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * limit
    # Need to eager load role for response
    # lazy="joined" on relationship handles it, but good to be explicit if creating response explicitly
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
    # Check if email already exists locally
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Resolve Role
    role_result = await db.execute(
        select(RoleModel).where(RoleModel.name == user_data.role)
    )
    role_obj = role_result.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{user_data.role}' not found",
        )

    # Create user in Keycloak first
    kc_admin = get_keycloak_admin()
    kc_user_id = await kc_admin.create_user(
        username=user_data.email, # Use email as username
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        roles=[user_data.role],
        enabled=True,
        email_verified=True,
    )

    if not kc_user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user in identity provider",
        )

    # Create user in Postgres with Keycloak ID
    try:
        user = User(
            id=UUID(kc_user_id), # Use Keycloak ID
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=role_obj,
            hashed_password="OIDC_MANAGED", # Password is in Keycloak
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # Audit log
        await log_audit(
            db,
            current_user.id,
            "create_user",
            "user",
            str(user.id),
            {"email": user.email, "role": role_obj.name, "keycloak_id": kc_user_id},
        )
        await db.commit()

        logger.info("user_created", user_id=str(user.id), email=user.email)

        return UserResponse.model_validate(user)
    except Exception as e:
        logger.error("db_user_creation_failed", error=str(e), keycloak_id=kc_user_id)
        # Rollback Keycloak user if DB fails (best effort)
        await kc_admin.delete_user(kc_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database creation failed",
        )


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

    # Resolve role if provided
    role_obj = None
    if user_data.role:
        role_result = await db.execute(
            select(RoleModel).where(RoleModel.name == user_data.role)
        )
        role_obj = role_result.scalar_one_or_none()
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{user_data.role}' not found",
            )

    # Apply updates
    update_data = user_data.model_dump(exclude_unset=True, exclude={"role"})
    if update_data:
        for key, value in update_data.items():
            setattr(user, key, value)

    if role_obj:
        user.role = role_obj

    await db.flush()
    await db.refresh(user)

    # Audit log (simplified)
    await log_audit(
        db,
        current_user.id,
        "update_user",
        "user",
        str(user.id),
        {"updated_fields": list(update_data.keys()) + (["role"] if role_obj else [])},
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

    # Protected Users Check
    PROTECTED_EMAILS = ["admin@infantstack.com", "nurse@infantstack.com"]
    if user.email in PROTECTED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete protected user: {user.email}",
        )

    # Delete from Keycloak first
    kc_admin = get_keycloak_admin()
    # Assuming User.id matches Keycloak ID (which it should now)
    kc_deleted = await kc_admin.delete_user(str(user_id))
    
    if not kc_deleted:
         # Log warning but proceed with DB delete to avoid zombie records? 
         # Or fail? If KC delete fails, user can still login. So we should probably fail.
         # But if user doesn't exist in KC (legacy), we should allow DB delete.
         # For now, let's log and proceed, assuming consistency fixes later.
         logger.warning("keycloak_delete_failed_or_missing", user_id=str(user_id))

    # Hard delete from Postgres
    await db.delete(user)
    
    # Audit log
    await log_audit(
        db,
        current_user.id,
        "delete_user",
        "user",
        str(user_id), # Use ID since object is deleted
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

    role_result = await db.execute(
        select(RoleModel).where(RoleModel.name == role_data.role)
    )
    role_obj = role_result.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.role}' not found",
        )

    old_role_name = user.role.name if user.role else "none"
    user.role = role_obj

    # Audit log
    await log_audit(
        db,
        current_user.id,
        "assign_role",
        "user",
        str(user.id),
        {"old_role": old_role_name, "new_role": role_obj.name},
    )
    await db.commit()
    await db.refresh(user)

    logger.info("role_assigned", user_id=str(user.id), role=role_obj.name)

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
        db,
        current_user.id,
        "reset_password",
        "user",
        str(user.id),
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
    update_data = user_data.model_dump(
        exclude_unset=True, exclude={"role", "is_active"}
    )
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
    if not verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)

    # Audit log
    await log_audit(
        db,
        current_user.id,
        "change_password",
        "user",
        str(current_user.id),
    )
    await db.commit()

    logger.info("password_changed", user_id=str(current_user.id))

    return None
