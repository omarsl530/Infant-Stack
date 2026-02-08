"""
SQLAlchemy ORM models for the Infant-Stack database.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .roles import Role


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
    room: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    discharged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paired_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    infant: Mapped["Infant"] = relationship(back_populates="pairings", lazy="joined")
    mother: Mapped["Mother"] = relationship(back_populates="pairings", lazy="joined")


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
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (Index("ix_movement_logs_tag_timestamp", "tag_id", "timestamp"),)


class Alert(Base):
    """Security and system alerts."""

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    alert_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity, name="alert_severity"))
    tag_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    reader_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)
    acknowledged_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )


# =============================================================================
# User Management
# =============================================================================


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
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id"),
        nullable=True,  # Nullable for now to avoiding breaking if migration missed something, but ideally permissions rely on it
    )
    role: Mapped["Role"] = relationship("Role", lazy="joined")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(
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
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (Index("ix_audit_logs_user_created", "user_id", "created_at"),)


# =============================================================================
# RTLS Position Tracking
# =============================================================================


class RTLSPosition(Base):
    """Real-time location system position data."""

    __tablename__ = "rtls_positions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tag_id: Mapped[str] = mapped_column(String(50), index=True)
    asset_type: Mapped[str] = mapped_column(
        String(20)
    )  # infant, mother, staff, equipment
    x: Mapped[float] = mapped_column()
    y: Mapped[float] = mapped_column()
    z: Mapped[float] = mapped_column(default=0.0)
    floor: Mapped[str] = mapped_column(String(20), index=True)
    accuracy: Mapped[float] = mapped_column(default=0.5)
    battery_pct: Mapped[int] = mapped_column(default=100)
    gateway_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rssi: Mapped[int | None] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_rtls_positions_tag_timestamp", "tag_id", "timestamp"),
        Index("ix_rtls_positions_floor_timestamp", "floor", "timestamp"),
    )


# =============================================================================
# Gate and Access Control
# =============================================================================


class GateState(str, Enum):
    """State of a security gate."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FORCED_OPEN = "FORCED_OPEN"
    HELD_OPEN = "HELD_OPEN"
    UNKNOWN = "UNKNOWN"


class Gate(Base):
    """Security gate/door entity."""

    __tablename__ = "gates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    gate_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    floor: Mapped[str] = mapped_column(String(20), index=True)
    zone: Mapped[str] = mapped_column(String(50))
    state: Mapped[GateState] = mapped_column(
        SQLEnum(GateState, name="gate_state"), default=GateState.CLOSED
    )
    last_state_change: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    camera_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class GateEventType(str, Enum):
    """Types of gate events."""

    BADGE_SCAN = "badge_scan"
    GATE_STATE = "gate_state"
    FORCED = "forced"
    HELD_OPEN = "held_open"


class GateEventResult(str, Enum):
    """Result of a gate access attempt."""

    GRANTED = "GRANTED"
    DENIED = "DENIED"


class GateEvent(Base):
    """Event log for gate access and state changes."""

    __tablename__ = "gate_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    gate_id: Mapped[str] = mapped_column(String(50), index=True)
    event_type: Mapped[GateEventType] = mapped_column(SQLEnum(GateEventType, name="gate_event_type", values_callable=lambda x: [e.value for e in x]))
    state: Mapped[GateState | None] = mapped_column(
        SQLEnum(GateState, name="gate_state"), nullable=True
    )
    previous_state: Mapped[GateState | None] = mapped_column(
        SQLEnum(GateState, name="gate_state"), nullable=True
    )
    badge_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[GateEventResult | None] = mapped_column(
        SQLEnum(GateEventResult, name="gate_event_result"), nullable=True
    )
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # IN, OUT
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )

    __table_args__ = (Index("ix_gate_events_gate_timestamp", "gate_id", "timestamp"),)


# =============================================================================
# Zones and Geofences
# =============================================================================


class ZoneType(str, Enum):
    """Type of security zone."""

    AUTHORIZED = "authorized"
    RESTRICTED = "restricted"
    EXIT = "exit"


class Zone(Base):
    """Geofence zone definition."""

    __tablename__ = "zones"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100))
    floor: Mapped[str] = mapped_column(String(20), index=True)
    zone_type: Mapped[ZoneType] = mapped_column(SQLEnum(ZoneType, name="zone_type", values_callable=lambda x: [e.value for e in x]))
    polygon: Mapped[list[dict]] = mapped_column(JSONB)  # List of {x, y} points
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


# =============================================================================
# Camera Management
# =============================================================================


class CameraStatus(str, Enum):
    """Status of a camera."""

    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class Camera(Base):
    """Camera entity linked to gates and zones."""

    __tablename__ = "cameras"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    camera_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    floor: Mapped[str] = mapped_column(String(20), index=True)
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gate_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    stream_url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[CameraStatus] = mapped_column(
        SQLEnum(CameraStatus, name="camera_status", values_callable=lambda x: [e.value for e in x]), default=CameraStatus.ONLINE
    )
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


# =============================================================================
# Floorplan Management
# =============================================================================


class Floorplan(Base):
    """Floorplan image and coordinate mapping."""

    __tablename__ = "floorplans"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    floor: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str] = mapped_column(String(500))
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()
    scale: Mapped[float] = mapped_column(default=1.0)  # pixels per meter
    origin_x: Mapped[float] = mapped_column(default=0.0)
    origin_y: Mapped[float] = mapped_column(default=0.0)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


# =============================================================================
# System Configuration
# =============================================================================


class ConfigType(str, Enum):
    """Type of configuration value."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


class SystemConfig(Base):
    """Dynamic system configuration settings."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    type: Mapped[ConfigType] = mapped_column(SQLEnum(ConfigType, name="configtype"))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
