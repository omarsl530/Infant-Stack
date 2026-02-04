"""
Device Gateway Service - MQTT Message Handler

Listens to MQTT topics for tag movement events and persists them to PostgreSQL.
This service is the central ingestion point for all IoT device messages.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime
from typing import Any
from uuid import uuid4

import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from shared_libraries.config import get_settings
from shared_libraries.logging import get_logger, setup_logging

# Initialize logging and configuration
setup_logging("device-gateway", "INFO")
logger = get_logger(__name__)
settings = get_settings()


class DeviceGateway:
    """MQTT-to-Database gateway for processing tag events."""

    def __init__(self) -> None:
        """Initialize the gateway with database and MQTT connections."""
        self.running = True
        self._setup_database()
        self._setup_mqtt()

    def _setup_database(self) -> None:
        """Set up database connection."""
        # Use synchronous engine for MQTT callback compatibility
        db_url = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("database_connected", host=settings.postgres_host)

    def _setup_mqtt(self) -> None:
        """Set up MQTT client with callbacks."""
        self.mqtt_client = mqtt.Client(
            client_id=f"device-gateway-{uuid4().hex[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict,
        reason_code: mqtt.ReasonCode,
        properties: Any,
    ) -> None:
        """Handle MQTT connection establishment."""
        if reason_code == 0:
            logger.info(
                "mqtt_connected",
                broker=settings.mqtt_broker,
                topic=settings.mqtt_topic_movements,
            )
            # Subscribe to movement events
            client.subscribe(settings.mqtt_topic_movements)
            # Subscribe to alert events
            client.subscribe(settings.mqtt_topic_alerts)
            # Subscribe to gate control events (from Terminal)
            client.subscribe("hospital/gates/+/control")
        else:
            logger.error("mqtt_connection_failed", reason_code=str(reason_code))

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: mqtt.ReasonCode,
        properties: Any,
    ) -> None:
        """Handle MQTT disconnection."""
        logger.warning("mqtt_disconnected", reason_code=str(reason_code))

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Process incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic

            logger.info(
                "message_received",
                topic=topic,
                tag_id=payload.get("tag_id"),
                event_type=payload.get("event"),
            )

            # Route message based on topic
            if "movements" in topic:
                self._handle_movement_event(payload, topic)
            elif "alerts" in topic:
                self._handle_alert_event(payload)
            elif "control" in topic:
                self._handle_gate_control_event(payload, topic)
            else:
                logger.warning("unknown_topic", topic=topic)

        except json.JSONDecodeError as e:
            logger.error(
                "invalid_json", error=str(e), payload=msg.payload.decode()[:100]
            )
        except Exception as e:
            logger.error("message_processing_error", error=str(e))

    def _handle_movement_event(self, payload: dict, topic: str) -> None:
        """Persist movement event to database."""
        session = self.Session()
        try:
            # Extract zone from topic (e.g., hospital/gate1/movements -> gate1)
            zone = topic.split("/")[1] if len(topic.split("/")) > 1 else None

            query = text("""
                INSERT INTO movement_logs (id, tag_id, reader_id, event_type, zone, metadata, timestamp)
                VALUES (:id, :tag_id, :reader_id, :event_type, :zone, :metadata, :timestamp)
            """)

            session.execute(
                query,
                {
                    "id": str(uuid4()),
                    "tag_id": payload.get("tag_id"),
                    "reader_id": payload.get("reader_id"),
                    "event_type": payload.get("event", "unknown"),
                    "zone": zone,
                    "metadata": json.dumps(payload.get("meta", {})),
                    "timestamp": datetime.utcnow(),
                },
            )
            session.commit()
            logger.info("movement_saved", tag_id=payload.get("tag_id"))

            # Check for unauthorized gate approach
            if payload.get("event") == "gate_approach":
                self._check_gate_authorization(payload)

        except Exception as e:
            session.rollback()
            logger.error("database_error", error=str(e))
        finally:
            session.close()

    def _handle_alert_event(self, payload: dict) -> None:
        """Persist alert event to database."""
        session = self.Session()
        try:
            query = text("""
                INSERT INTO alerts (id, alert_type, severity, tag_id, reader_id, message, metadata, created_at)
                VALUES (:id, :alert_type, :severity, :tag_id, :reader_id, :message, :metadata, :created_at)
            """)

            session.execute(
                query,
                {
                    "id": str(uuid4()),
                    "alert_type": payload.get("type", "unknown"),
                    "severity": payload.get("severity", "warning"),
                    "tag_id": payload.get("tag_id"),
                    "reader_id": payload.get("reader_id"),
                    "message": payload.get("message", "Alert triggered"),
                    "metadata": json.dumps(payload.get("meta", {})),
                    "created_at": datetime.utcnow(),
                },
            )
            session.commit()
            logger.info("alert_saved", alert_type=payload.get("type"))

        except Exception as e:
            session.rollback()
            logger.error("alert_save_error", error=str(e))
        finally:
            session.close()

    def _handle_gate_control_event(self, payload: dict, topic: str) -> None:
        """Handle gate control commands (UNLOCK, ALARM, CLEAR)."""
        session = self.Session()
        try:
            # Extract gate_id from topic (hospital/gates/gate_1/control)
            # topic structure: hospital/gates/{gate_id}/control
            parts = topic.split("/")
            gate_id = parts[2] if len(parts) > 2 else "unknown"
            
            command = payload.get("command")
            
            event_type = "gate_state"
            state = None
            
            if command == "UNLOCK":
                state = "OPEN"
                event_type = "gate_state"
            elif command == "ALARM":
                state = "FORCED_OPEN" 
                event_type = "forced"
                # Create a high severity alert
                self._publish_alert({
                    "type": "security_alarm",
                    "severity": "critical",
                    "message": f"Security Alarm triggered at {gate_id}",
                    "reader_id": gate_id,
                    "tag_id": None
                })
            elif command == "CLEAR":
                state = "CLOSED"
                event_type = "gate_state"

            logger.info("gate_control", gate_id=gate_id, command=command)
            
            # Log to gate_events
            query = text("""
                INSERT INTO gate_events (id, gate_id, event_type, state, timestamp)
                VALUES (:id, :gate_id, :event_type, :state, :timestamp)
            """)
            
            session.execute(query, {
                "id": str(uuid4()),
                "gate_id": gate_id,
                "event_type": event_type,
                "state": state,
                "timestamp": datetime.utcnow()
            })
            
            # Update Gate status if exists
            update_query = text("UPDATE gates SET state = :state, last_state_change = :timestamp WHERE gate_id = :gate_id")
            session.execute(update_query, {
                "state": state if state else "UNKNOWN",
                "timestamp": datetime.utcnow(),
                "gate_id": gate_id
            })
            
            session.commit()

        except Exception as e:
            session.rollback()
            logger.error("gate_control_error", error=str(e))
        finally:
            session.close()

    def _check_gate_authorization(self, payload: dict) -> None:
        """Check if tag is authorized to exit through gate."""
        session = self.Session()
        try:
            tag_id = payload.get("tag_id")

            # Check if infant tag has active pairing
            query = text("""
                SELECT p.id, m.tag_id as mother_tag_id
                FROM pairings p
                JOIN infants i ON p.infant_id = i.id
                JOIN mothers m ON p.mother_id = m.id
                WHERE i.tag_id = :tag_id AND p.status = 'active'
            """)

            result = session.execute(query, {"tag_id": tag_id}).fetchone()

            if not result:
                # No active pairing - trigger alert
                self._publish_alert(
                    {
                        "type": "unauthorized_gate_approach",
                        "severity": "critical",
                        "tag_id": tag_id,
                        "reader_id": payload.get("reader_id"),
                        "message": f"Infant tag {tag_id} approaching gate without authorized pairing",
                    }
                )
                logger.warning("unauthorized_gate_approach", tag_id=tag_id)

        except Exception as e:
            logger.error("authorization_check_error", error=str(e))
        finally:
            session.close()

    def _publish_alert(self, alert: dict) -> None:
        """Publish alert message to MQTT."""
        self.mqtt_client.publish(
            settings.mqtt_topic_alerts,
            json.dumps(alert),
            qos=1,
        )

    def start(self) -> None:
        """Start the gateway service."""
        logger.info("starting_device_gateway")

        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(
                settings.mqtt_broker,
                settings.mqtt_port,
                keepalive=60,
            )
        except Exception as e:
            logger.error("mqtt_connect_error", error=str(e))
            raise

        # Start MQTT loop
        self.mqtt_client.loop_start()
        logger.info("device_gateway_started")

        # Keep running until stopped
        while self.running:
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))

    def stop(self) -> None:
        """Stop the gateway service gracefully."""
        logger.info("stopping_device_gateway")
        self.running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        self.engine.dispose()
        logger.info("device_gateway_stopped")


def main() -> None:
    """Entry point for the device gateway service."""
    gateway = DeviceGateway()

    def signal_handler(sig: int, frame: Any) -> None:
        logger.info("shutdown_signal_received", signal=sig)
        gateway.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    gateway.start()


if __name__ == "__main__":
    main()
