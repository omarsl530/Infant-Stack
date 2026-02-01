from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared_libraries.database import get_db
from shared_libraries.auth import (
    require_admin, 
    CurrentUser,
    Permissions,
    require_permission
)
from shared_libraries.logging import get_logger
from database.orm_models.models import User
from database.orm_models.roles import Role as RoleModel

# Setup Logger
logger = get_logger(__name__)

# Router
router = APIRouter()

# =============================================================================
# Pydantic Schemas
# =============================================================================

class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Unique role name")
    description: Optional[str] = Field(None, max_length=255)
    permissions: Dict[str, List[str]] = Field(
        default_factory=dict, 
        description="JSON mapping of resources to actions, e.g. {'user': ['read', 'write']}"
    )

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    permissions: Optional[Dict[str, List[str]]] = None

class RoleResponse(RoleBase):
    id: UUID
    is_system: bool
    created_at: datetime
    updated_at: datetime
    user_count: int = 0

    class Config:
        from_attributes = True

# =============================================================================
# Routes
# =============================================================================

@router.get("/permissions", response_model=List[str])
async def list_available_permissions(
    _current_user: CurrentUser = Depends(require_admin)
):
    """
    List all available system permission constants.
    These are the granular permissions that can be assigned to roles.
    """
    # Extract constants from Permissions class usually defined in auth.py
    # We'll just inspect the class attributes that are uppercase
    perms = [
        value for name, value in vars(Permissions).items() 
        if name.isupper() and isinstance(value, str)
    ]
    return sorted(perms)


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin) # Only admin can list roles
):
    """List all defined roles."""
    query = select(RoleModel).options(
        # Load user count? Or do separate query.
        # selectinload(RoleModel.users) # Optimizes loading users relationship
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    roles = result.scalars().all()
    
    # Calculate user counts
    # This might be N+1 if we loop. Better to do a group by count query or fetch eager.
    # For now, simplistic approach or just don't return count in list if not needed.
    # But Admin UI usually wants to know if role is used.
    
    response = []
    for role in roles:
        # Count users in this role
        # We can do a count query for each or assume we don't have millions of users for now.
        user_count_query = select(func.count()).select_from(User).where(User.role_id == role.id)
        count_res = await db.execute(user_count_query)
        count = count_res.scalar()
        
        role_resp = RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            is_system=role.is_system,
            created_at=role.created_at,
            updated_at=role.updated_at,
            user_count=count
        )
        response.append(role_resp)
        
    return response


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Create a new custom role."""
    # Check if name exists
    existing = await db.execute(select(RoleModel).where(RoleModel.name == role_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with name '{role_data.name}' already exists"
        )
    
    new_role = RoleModel(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions,
        is_system=False # Custom roles are not system
    )
    
    db.add(new_role)
    try:
        await db.commit()
        await db.refresh(new_role)
        logger.info("role_created", admin_id=current_user.id, role_name=new_role.name)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
        
    return RoleResponse(
        id=new_role.id, 
        name=new_role.name, 
        description=new_role.description, 
        permissions=new_role.permissions, 
        is_system=new_role.is_system, 
        created_at=new_role.created_at, 
        updated_at=new_role.updated_at,
        user_count=0
    )


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin)
):
    """Get details of a specific role."""
    role = await db.get(RoleModel, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    # Get user count
    user_count_query = select(func.count()).select_from(User).where(User.role_id == role.id)
    count_res = await db.execute(user_count_query)
    count = count_res.scalar()
    
    response = RoleResponse.model_validate(role)
    response.user_count = count
    return response


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Update an existing role."""
    role = await db.get(RoleModel, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role.is_system:
        # We might allows editing system role permissions but NOT name.
        if role_data.name and role_data.name != role.name:
            raise HTTPException(
                status_code=400, 
                detail="Cannot rename system roles"
            )
            
    # Check name uniqueness if changing name
    if role_data.name and role_data.name != role.name:
         existing = await db.execute(select(RoleModel).where(RoleModel.name == role_data.name))
         if existing.scalar_one_or_none():
             raise HTTPException(status_code=400, detail="Role name already in use")
    
    role_dict = role_data.model_dump(exclude_unset=True)
    for key, value in role_dict.items():
        setattr(role, key, value)
        
    try:
        await db.commit()
        await db.refresh(role)
        logger.info("role_updated", admin_id=current_user.id, role_id=str(role_id))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    # Get count
    user_count_query = select(func.count()).select_from(User).where(User.role_id == role.id)
    count_res = await db.execute(user_count_query)
    count = count_res.scalar()
    
    response = RoleResponse.model_validate(role)
    response.user_count = count
    return response


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """Delete a custom role. Cannot delete system roles or roles in use."""
    role = await db.get(RoleModel, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
        
    # Check if used
    user_count_query = select(func.count()).select_from(User).where(User.role_id == role.id)
    count_res = await db.execute(user_count_query)
    count = count_res.scalar()
    
    if count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role assigned to {count} users. Reassign them first."
        )
        
    await db.delete(role)
    await db.commit()
    logger.info("role_deleted", admin_id=current_user.id, role_id=str(role_id))
