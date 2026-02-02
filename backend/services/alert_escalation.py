"""
Alert Escalation Service.

Runs as a background task to monitor critical alerts and escalate them if unacknowledged.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import and_, select

from database.orm_models.models import Alert, AlertSeverity, AuditLog
from shared_libraries.database import async_session_factory
from shared_libraries.logging import get_logger

logger = get_logger(__name__)

ESCALATION_THRESHOLD_MINUTES = 5
CHECK_INTERVAL_SECONDS = 60


async def check_for_escalations():
    """Check for unacknowledged critical alerts and escalate them."""
    logger.info("alert_escalation_check_started")

    async with async_session_factory() as db:
        try:
            # Find unacknowledged critical alerts older than threshold
            threshold_time = datetime.utcnow() - timedelta(
                minutes=ESCALATION_THRESHOLD_MINUTES
            )

            query = select(Alert).where(
                and_(
                    Alert.severity == AlertSeverity.CRITICAL,
                    Alert.acknowledged.is_(False),
                    Alert.created_at < threshold_time,
                    # Optimization: Maybe filter out already escalated ones if we had a status flag
                    # For now, we'll just log an audit event, so we need to check if we already logged it to avoid spam
                    # But checking audit logs is expensive.
                    # Ideally Alert model would have 'escalation_level' or 'last_escalated_at'.
                    # For MVP, we will assume we just log it. To prevent spam, we might need a cache or model update.
                    # Let's add a dynamic check: 'extra_data' -> 'escalated': True
                )
            )

            result = await db.execute(query)
            overdue_alerts = result.scalars().all()

            for alert in overdue_alerts:
                # Check if already escalated
                if alert.extra_data and alert.extra_data.get("escalated"):
                    continue

                logger.warning(
                    "escalating_alert", alert_id=alert.id, type=alert.alert_type
                )

                # 1. Update Alert to mark as escalated
                if not alert.extra_data:
                    alert.extra_data = {}
                alert.extra_data["escalated"] = True
                alert.extra_data["escalated_at"] = datetime.utcnow().isoformat()

                # 2. Create Audit Log Entry
                audit = AuditLog(
                    action="ALERT_ESCALATED",
                    resource_type="alert",
                    resource_id=str(alert.id),
                    details={
                        "reason": f"Unacknowledged for > {ESCALATION_THRESHOLD_MINUTES}m",
                        "alert_type": alert.alert_type,
                        "original_severity": alert.severity.value,
                    },
                    user_id=None,  # System action
                )
                db.add(audit)

                # 3. In a real system, send SMS/Email/WebSocket Broadcast here

            await db.commit()

        except Exception as e:
            logger.error("alert_escalation_failed", error=str(e))


async def start_alert_escalation_worker():
    """Start the background worker loop."""
    logger.info("alert_escalator_starting")
    while True:
        try:
            await check_for_escalations()
        except Exception as e:
            logger.error("alert_escalator_loop_error", error=str(e))

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
