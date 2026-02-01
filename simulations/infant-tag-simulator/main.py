"""
Infant Tag Simulator - Generates realistic MQTT messages for testing.

Usage:
    python main.py --tags 5 --interval 2

This simulator creates virtual infant tags that publish movement events
to the MQTT broker, simulating the behavior of physical RFID/BLE tags.
"""

import argparse
import json
import random
import signal
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List

import paho.mqtt.client as mqtt


@dataclass
class VirtualTag:
    """Represents a virtual infant tag."""
    tag_id: str
    current_zone: str
    battery_level: int
    last_reader: str
    paired_mother_tag: str


# Zone definitions
ZONES = ["nursery", "ward_a", "ward_b", "corridor_1", "corridor_2", "gate_1", "gate_2"]
READERS = ["READER_01", "READER_02", "READER_03", "READER_04", "GATE_READER_1", "GATE_READER_2"]
EVENT_TYPES = ["proximity", "movement", "button_press", "low_battery", "gate_approach"]


def create_virtual_tags(count: int) -> List[VirtualTag]:
    """Create a list of virtual tags."""
    tags = []
    for i in range(1, count + 1):
        tag = VirtualTag(
            tag_id=f"INF-{i:03d}",
            current_zone=random.choice(ZONES[:4]),  # Start in safe zones
            battery_level=random.randint(50, 100),
            last_reader=random.choice(READERS[:4]),
            paired_mother_tag=f"MOM-{i:03d}",
        )
        tags.append(tag)
    return tags


def simulate_tag_movement(tag: VirtualTag) -> dict:
    """Simulate a single tag movement event."""
    # 10% chance to move to adjacent zone
    if random.random() < 0.1:
        tag.current_zone = random.choice(ZONES)
        tag.last_reader = random.choice(READERS)

    # Drain battery slowly
    if random.random() < 0.01:
        tag.battery_level = max(0, tag.battery_level - 1)

    # Determine event type
    if tag.current_zone.startswith("gate"):
        event_type = "gate_approach"
    elif tag.battery_level < 20:
        event_type = "low_battery"
    elif random.random() < 0.8:
        event_type = "proximity"
    else:
        event_type = random.choice(EVENT_TYPES)

    return {
        "tag_id": tag.tag_id,
        "reader_id": tag.last_reader,
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "meta": {
            "zone": tag.current_zone,
            "battery": tag.battery_level,
            "rssi": random.randint(-70, -30),
            "paired_with": tag.paired_mother_tag,
        },
    }


class TagSimulator:
    """Main simulator class."""

    def __init__(self, broker: str, port: int, tag_count: int, interval: float):
        self.broker = broker
        self.port = port
        self.tag_count = tag_count
        self.interval = interval
        self.running = True
        self.tags = create_virtual_tags(tag_count)
        self.client = mqtt.Client(
            client_id="infant-tag-simulator",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
        else:
            print(f"❌ Connection failed: {reason_code}")

    def start(self):
        """Start the simulation."""
        self.client.on_connect = self.on_connect

        print(f"🏷️  Starting Infant Tag Simulator")
        print(f"   Tags: {self.tag_count}")
        print(f"   Interval: {self.interval}s")
        print(f"   Broker: {self.broker}:{self.port}")
        print("-" * 40)

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return

        while self.running:
            for tag in self.tags:
                if not self.running:
                    break

                event = simulate_tag_movement(tag)
                topic = f"hospital/{tag.current_zone}/movements"

                self.client.publish(topic, json.dumps(event), qos=1)

                print(f"📡 [{tag.tag_id}] {event['event']} @ {tag.current_zone}")

            time.sleep(self.interval)

    def stop(self):
        """Stop the simulation."""
        print("\n⏹️  Stopping simulator...")
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Infant Tag Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--tags", type=int, default=5, help="Number of virtual tags")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between events")
    args = parser.parse_args()

    simulator = TagSimulator(args.broker, args.port, args.tags, args.interval)

    def signal_handler(sig, frame):
        simulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    simulator.start()


if __name__ == "__main__":
    main()
