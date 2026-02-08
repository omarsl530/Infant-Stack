import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from shared_libraries.database import async_session_factory
from database.orm_models.models import Zone
from shared_libraries.logging import get_logger

logger = get_logger("reset_zones")

async def reset_zones():
    logger.info("Connecting to DB to wipe zones...")
    async with async_session_factory() as db:
        try:
            await db.execute(delete(Zone))
            await db.commit()
            logger.info("Successfully deleted all zones.")
        except Exception as e:
            logger.error(f"Failed to delete zones: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(reset_zones())
