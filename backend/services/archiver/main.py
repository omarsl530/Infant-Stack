import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Type

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import models
from database.orm_models.models import MovementLog, RTLSPosition

# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@localhost/infant_stack"
)
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "./archive")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

logger = structlog.get_logger()

# Setup explicit async engine for this service (independent of shared_libraries if needed,
# but could reuse if shared_libs is importable. Using direct setup for standalone reliability)
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def serialize_record(record) -> dict:
    """Helper to serialize SQLAlchemy model to dict."""
    data = {}
    for col in record.__table__.columns:
        val = getattr(record, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, (int, float, str, bool, type(None))):
            pass
        else:
            val = str(val)  # Fallback
        data[col.name] = val
    return data


async def archive_model(model: Type, date_field, model_name: str):
    """
    Archives records older than RETENTION_DAYS to JSONL and deletes them.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    logger.info("starting_archive_job", model=model_name, cutoff=cutoff_date)

    archive_path = Path(ARCHIVE_DIR)
    archive_path.mkdir(parents=True, exist_ok=True)

    filename = f"{model_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    filepath = archive_path / filename

    total_archived = 0

    async with AsyncSessionLocal() as session:
        # Stream records to file
        try:
            with open(filepath, "w") as f:
                # Query in batches or stream
                stmt = (
                    select(model)
                    .where(date_field < cutoff_date)
                    .execution_options(yield_per=BATCH_SIZE)
                )
                result = await session.stream(stmt)

                async for row in result:
                    record = row[0]
                    data = serialize_record(record)
                    f.write(json.dumps(data) + "\n")
                    total_archived += 1

            if total_archived > 0:
                logger.info(
                    "archived_records_to_file", count=total_archived, file=str(filepath)
                )

                # Delete from DB
                # Note: Delete with limit is tricky in standard SQL/SQLAlchemy without specific dialect support or loops.
                # For safety and Postgres performance, we delete in chunks using ID subqueries or just simple delete if volume isn't massive logic.
                # Given 'BATCH_SIZE', let's do a bulk delete for simplicity, but in a real massive DB, we might want to loop deletes.

                delete_stmt = delete(model).where(date_field < cutoff_date)
                await session.execute(delete_stmt)
                await session.commit()
                logger.info(
                    "deleted_records_from_db", model=model_name, count=total_archived
                )
            else:
                logger.info("no_records_to_archive", model=model_name)
                # Cleanup empty file
                if filepath.exists():
                    filepath.unlink()

        except Exception as e:
            logger.error("archive_failed", error=str(e), model=model_name)
            await session.rollback()


async def run_archive_cycle():
    """Runs archiving for all configured models."""
    logger.info("archive_cycle_started")
    await archive_model(RTLSPosition, RTLSPosition.timestamp, "rtls_positions")
    await archive_model(MovementLog, MovementLog.timestamp, "movement_logs")
    logger.info("archive_cycle_completed")


def job_wrapper():
    """Sync wrapper for async job."""
    asyncio.run(run_archive_cycle())


def main():
    logger.info("archiver_service_starting", retention_days=RETENTION_DAYS)

    scheduler = BlockingScheduler()
    # Schedule to run daily at 3 AM
    scheduler.add_job(job_wrapper, "cron", hour=3, minute=0)

    # Also run once on startup for verification (optional, maybe controlled by flag? For now, let's just log)
    # job_wrapper() # Uncomment to force run on startup

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
