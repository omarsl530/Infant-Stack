
import asyncio
from sqlalchemy import select, func
from database.orm_models.models import Infant, Mother, TagStatus
from shared_libraries.database import get_db

async def check_active_tags():
    async for db in get_db():
        # Check all distinct tag statuses
        infant_statuses = await db.execute(select(Infant.tag_status, func.count(Infant.id)).group_by(Infant.tag_status))
        mother_statuses = await db.execute(select(Mother.tag_status, func.count(Mother.id)).group_by(Mother.tag_status))
        
        print("\n--- Infant Statuses ---")
        for status, count in infant_statuses.all():
            print(f"Status: '{status}' (Type: {type(status)}), Count: {count}")
            
        print("\n--- Mother Statuses ---")
        for status, count in mother_statuses.all():
            print(f"Status: '{status}' (Type: {type(status)}), Count: {count}")

        # Check raw values if enum mapping is weird
        # (This relies on SQLAlchemy handling the enum, but string matching might be key)
        
        break

if __name__ == "__main__":
    asyncio.run(check_active_tags())
