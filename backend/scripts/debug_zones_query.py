import asyncio
import logging
import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from shared_libraries.database import async_session_factory
from database.orm_models.models import Zone

class ZoneResponse(BaseModel):
    """Response model for zone data."""
    id: UUID
    name: str
    floor: str
    zone_type: str
    polygon: list[dict]
    color: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_zones")

async def test_query():
    logger.info("Connecting to DB...")
    async with async_session_factory() as db:
        logger.info("Executing select(Zone)...")
        try:
            result = await db.execute(select(Zone))
            zones = result.scalars().all()
            logger.info(f"Found {len(zones)} zones")
            
            for i, z in enumerate(zones):
                # Inspect zone_type
                try:
                    # Simulation of API logic
                    z_resp = ZoneResponse(
                        id=z.id,
                        name=z.name,
                        floor=z.floor,
                        zone_type=z.zone_type.value,
                        polygon=z.polygon,
                        color=z.color,
                        is_active=z.is_active,
                        created_at=z.created_at,
                        updated_at=z.updated_at,
                    )
                    logger.info(f"Zone {i} Pydantic Validation Success")
                except Exception as e:
                    logger.error(f"Zone {i} Pydantic Validation Failed: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            logger.error(f"Query failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query())
