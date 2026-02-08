"""
Seed geofence zones into the database.

Creates RESTRICTED and EXIT zones for testing geofence alerts.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_models.models import Zone, ZoneType
from shared_libraries.database import async_session_factory
from shared_libraries.logging import get_logger

logger = get_logger(__name__)


SEED_ZONES = [
    {
        "name": "Restricted Area - Server Room",
        "floor": "1",
        "zone_type": ZoneType.RESTRICTED,
        "polygon": [
            {"x": 900.0, "y": 900.0},
            {"x": 1000.0, "y": 900.0},
            {"x": 1000.0, "y": 1000.0},
            {"x": 900.0, "y": 1000.0},
        ],
        "color": "#FF0000",
        "is_active": True,
    },
    {
        "name": "Main Exit",
        "floor": "1",
        "zone_type": ZoneType.EXIT,
        "polygon": [
            {"x": 0.0, "y": 0.0},
            {"x": 50.0, "y": 0.0},
            {"x": 50.0, "y": 50.0},
            {"x": 0.0, "y": 50.0},
        ],
        "color": "#FFA500",
        "is_active": True,
    },
    {
        "name": "Emergency Exit",
        "floor": "1",
        "zone_type": ZoneType.EXIT,
        "polygon": [
            {"x": 500.0, "y": 0.0},
            {"x": 550.0, "y": 0.0},
            {"x": 550.0, "y": 50.0},
            {"x": 500.0, "y": 50.0},
        ],
        "color": "#FFA500",
        "is_active": True,
    },
    {
        "name": "Maternity Ward",
        "floor": "1",
        "zone_type": ZoneType.AUTHORIZED,
        "polygon": [
            {"x": 100.0, "y": 100.0},
            {"x": 400.0, "y": 100.0},
            {"x": 400.0, "y": 400.0},
            {"x": 100.0, "y": 400.0},
        ],
        "color": "#00FF00",
        "is_active": True,
    },
]


async def seed_zones(db: AsyncSession) -> None:
    """Seed zones into the database."""
    for zone_data in SEED_ZONES:
        # Check if zone already exists by name
        result = await db.execute(
            select(Zone).where(Zone.name == zone_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Zone '{zone_data['name']}' already exists, skipping")
            continue
        
        zone = Zone(**zone_data)
        db.add(zone)
        logger.info(f"Created zone: {zone_data['name']} ({zone_data['zone_type'].value})")
    
    await db.commit()
    logger.info("Zone seeding completed!")


async def main():
    """Main entry point."""
    print("Starting zone seeding...", flush=True)
    logger.info("Starting zone seeding...")
    
    try:
        async with async_session_factory() as db:
            await seed_zones(db)
        
        # Verify zones were created
        async with async_session_factory() as db:
            result = await db.execute(select(Zone))
            zones = result.scalars().all()
            print(f"Total zones in database: {len(zones)}", flush=True)
            for zone in zones:
                msg = f"  - {zone.name} ({zone.zone_type.value}) on floor {zone.floor}"
                print(msg, flush=True)
                logger.info(msg)
    except Exception as e:
        print(f"Error seeding zones: {e}", flush=True)
        logger.error(f"Error seeding zones: {e}")


if __name__ == "__main__":
    asyncio.run(main())
