"""
SQLAlchemy ORM models for the Infant-Stack database.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class TagStatus(str, Enum):
    """Status of an RFID/BLE tag."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ALERT = "ALERT"
    MAINTENANCE = "MAINTENANCE"


class PairingStatus(str, Enum):
    """Status of infant-mother pairing."""
    ACTIVE = "ACTIVE"
    DISCHARGED = "DISCHARGED"
    SUSPENDED = "SUSPENDED"


class AlertSeverity(str, Enum):
    """Severity level of alerts."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# =============================================================================
# Core Entity Models
# =============================================================================

class Infant(Base):
    """Infant record with associated tag."""
    
    __tablename__ = "infants"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tag_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    medical_record_number: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ward: Mapped[str] = mapped_column(String(50))
    room: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tag_status: Mapped[TagStatus] = mapped_column(
        SQLEnum(TagStatus, name="tag_status"), default=TagStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    pairings: Mapped[list["Pairing"]] = relationship(
        back_populates="infant", lazy="joined"
    )


class Mother(Base):
    """Mother/Guardian entity."""
    
    __tablename__ = "mothers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tag_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    medical_record_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ward: Mapped[str] = mapped_column(String(50))
    room: Mapped[str] = mapped_column(String(20))
    tag_status: Mapped[TagStatus] = mapped_column(
        SQLEnum(TagStatus, name="tag_status"), default=TagStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    pairings: Mapped[list["Pairing"]] = relationship(
        back_populates="mother", lazy="joined"
    )


class Pairing(Base):
    """Active pairing between infant and mother tags."""
    
    __tablename__ = "pairings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    infant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("infants.id"), index=True
    )
    mother_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mothers.id"), index=True
    )
    status: Mapped[PairingStatus] = mapped_column(
        SQLEnum(PairingStatus, name="pairing_status"), default=PairingStatus.ACTIVE
    )
    paired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    discharged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paired_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    infant: Mapped["Infant"] = relationship(
        back_populates="pairings", lazy="joined"
    )
    mother: Mapped["Mother"] = relationship(
        back_populates="pairings", lazy="joined"
    )


# =============================================================================
# Movement and Event Tracking
# =============================================================================

class MovementLog(Base):
    """Log of tag movement events from RTLS readers."""
    
    __tablename__ = "movement_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tag_id: Mapped[str] = mapped_column(String(50), index=True)
    reader_id: Mapped[str] = mapped_column(String(50), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_movement_logs_tag_timestamp", "tag_id", "timestamp"),
    )


class Alert(Base):
    """Security and system alerts."""
    
    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    alert_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity))
    tag_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    reader_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)
    acknowledged_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )


# =============================================================================
# User Management
# =============================================================================

class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    NURSE = "nurse"
    SECURITY = "security"
    VIEWER = "viewer"


class User(Base):
    """System users with role-based access."""
    
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(SQLEnum(Role), default=Role.VIEWER)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# =============================================================================
# Audit Logging
# =============================================================================

class AuditLog(Base):
    """Audit trail for all sensitive operations."""
    
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )
