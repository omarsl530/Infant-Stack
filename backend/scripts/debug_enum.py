
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_libraries.database import async_session_factory
from sqlalchemy import text

async def check_enum():
    async with async_session_factory() as db:
        try:
            result = await db.execute(text(
                "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'zone_type'"
            ))
            labels = result.scalars().all()
            print(f"Valid labels for zone_type: {labels}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_enum())
