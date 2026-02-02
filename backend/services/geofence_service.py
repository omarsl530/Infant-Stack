"""
Geofencing Service.

Handles logic for checking if tags are entering/exiting zones and triggering alerts.
"""

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import (
    Alert,
    AlertSeverity,
    Infant,
    Zone,
    ZoneType,
)
from shared_libraries.logging import get_logger

logger = get_logger(__name__)


def is_point_in_polygon(x: float, y: float, polygon: list[dict[str, float]]) -> bool:
    """
    Check if a point (x, y) is inside a polygon using Ray Casting algorithm.
    params:
        x, y: Point coordinates
        polygon: List of dicts [{'x': 1, 'y': 1}, ...]
    """
    if not polygon:
        return False

    num_vertices = len(polygon)
    inside = False

    p1 = polygon[0]
    p1x, p1y = p1["x"], p1["y"]

    for i in range(1, num_vertices + 1):
        p2 = polygon[i % num_vertices]
        p2x, p2y = p2["x"], p2["y"]

        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside

        p1x, p1y = p2x, p2y

    return inside


async def check_geofence(
    db: AsyncSession, tag_id: str, asset_type: str, x: float, y: float, floor: str
) -> list[Alert]:
    """
    Check if the given position violates any geofence rules.
    Returns a list of generated alerts.
    """
    alerts_generated = []

    # 1. Fetch active zones for this floor
    query = select(Zone).where(and_(Zone.floor == floor, Zone.is_active.is_(True)))
    result = await db.execute(query)
    zones = result.scalars().all()

    if not zones:
        return []

    # 2. Check each zone
    for zone in zones:
        # Simplistic approach: If in restricted zone -> ALERT
        # A more complex one would track state (enter/exit events)
        # For this phase, we just alert if 'inside' a Restricted zone

        if zone.zone_type == ZoneType.RESTRICTED:
            # Only care if tag is inside
            if is_point_in_polygon(x, y, zone.polygon):
                logger.warning("geofence_violation", tag_id=tag_id, zone=zone.name)

                # Create Alert
                # Check duplication: In real system, we'd debounce this (don't alert every second)
                # For now, we rely on the client or subsequent processing to handle deduplication
                # OR we check if there is arguably an active unacknowledged alert for this tag+zone recently.

                # Simple Deduplication: Check if there is an unacknowledged alert for this tag & zone in the last minute
                # Skipping for MVP performance, but good to note.

                alert_msg = f"Unauthorized access: Tag {tag_id} ({asset_type}) detected in Restricted Zone: {zone.name}"

                alert = Alert(
                    alert_type="GEOFENCE_VIOLATION",
                    severity=AlertSeverity.CRITICAL,
                    tag_id=tag_id,
                    message=alert_msg,
                    extra_data={
                        "zone_id": str(zone.id),
                        "zone_name": zone.name,
                        "x": x,
                        "y": y,
                        "floor": floor,
                    },
                )
                db.add(alert)
                alerts_generated.append(alert)

        elif zone.zone_type == ZoneType.EXIT:
            if is_point_in_polygon(x, y, zone.polygon):
                # Exit logic (check if discharged)
                # Fetch infant status
                if asset_type == "infant":
                    # Need to join with Infant table
                    res = await db.execute(
                        select(Infant).where(Infant.tag_id == tag_id)
                    )
                    infant = res.scalar_one_or_none()
                    if infant:
                        # logic: if not discharged -> Abduction Alert
                        # Assuming 'Pairing' has discharge info.
                        # This is complex, will stick to generic alert for now.
                        alert = Alert(
                            alert_type="EXIT_DETECTED",
                            severity=AlertSeverity.WARNING,  # Warning until proven abduction
                            tag_id=tag_id,
                            message=f"Tag {tag_id} detected at Exit: {zone.name}",
                            extra_data={"zone": zone.name},
                        )
                        db.add(alert)
                        alerts_generated.append(alert)

    return alerts_generated
