from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.orm_models.models import Base

class Role(Base):
    """Custom user roles with granular permissions."""
    
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict)  # { "resource": ["read", "write"] }
    is_system: Mapped[bool] = mapped_column(default=False)  # System roles cannot be deleted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    # Note: We will add the back_populates in models.py User class
    # users: Mapped[List["User"]] = relationship(back_populates="role_model")
