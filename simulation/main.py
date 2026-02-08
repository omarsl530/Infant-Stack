#!/usr/bin/env python3
"""
Infant Security & Mother-Infant Pairing Ecosystem - IoT Simulation Suite

This script provides a comprehensive asyncio-based simulation for testing the backend
APIs of the Infant Security system. It simulates all IoT devices described in the
System Specification Document (SSD) Section 11.

Requires: aiohttp (pip install aiohttp)

Configuration:
    - BACKEND_URL: Base URL of the backend API (default: http://localhost:8000)
    - NUM_INFANTS: Number of infant tags to simulate (default: 50)
    - NUM_READERS: Number of RTLS readers to simulate (default: 10)
    - FAST_MODE: Set to "1" for shorter timers (CI testing)
    - DEBUG_MODE: Set to "1" for verbose DEBUG logging
    - RANDOM_SEED: Seed for reproducible simulations (optional)

Usage:
    python3 main.py
    
    # Fast mode for CI:
    FAST_MODE=1 python3 main.py
    
    # With custom backend:
    BACKEND_URL=http://api.example.com:8080 python3 main.py
"""

import asyncio
import base64
import json
import logging
import os
import random
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp is required. Install with: pip install aiohttp")
    sys.exit(1)


# =============================================================================
# CONFIGURATION BLOCK
# =============================================================================
# Modify these values or set environment variables to customize the simulation.

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
NUM_INFANTS = int(os.environ.get("NUM_INFANTS", "50"))
NUM_READERS = int(os.environ.get("NUM_READERS", "10"))
NUM_ZONES = int(os.environ.get("NUM_ZONES", "10"))

# Generate zone list
ZONES = [f"zone_{i+1}" for i in range(NUM_ZONES)]

# Fast mode reduces all timers for CI testing
FAST_MODE = os.environ.get("FAST_MODE", "0") == "1"
DEBUG_MODE = os.environ.get("DEBUG_MODE", "0") == "1"

# Timing multiplier (0.1x for fast mode, 1x for normal)
TIME_SCALE = 0.1 if FAST_MODE else 1.0

# Seed random for reproducibility if specified
RANDOM_SEED = os.environ.get("RANDOM_SEED")
if RANDOM_SEED:
    random.seed(int(RANDOM_SEED))

# HTTP retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 0.5


# =============================================================================
# LOGGING SETUP
# =============================================================================

log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)

# Reduce aiohttp logging noise
logging.getLogger("aiohttp").setLevel(logging.WARNING)


# =============================================================================
# BEACON HUB - In-process Pub/Sub for beacon broadcasting
# =============================================================================

class BeaconHub:
    """
    Lightweight in-process pub/sub hub for broadcasting beacons from InfantTags
    to RTLSReaders. Uses asyncio.Queue for each subscriber to decouple timing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BeaconHub")
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """
        Subscribe to receive beacons. Returns a Queue that will receive all beacons.
        """
        async with self._lock:
            if subscriber_id not in self._subscribers:
                self._subscribers[subscriber_id] = asyncio.Queue(maxsize=1000)
                self.logger.debug(f"Subscriber {subscriber_id} registered")
            return self._subscribers[subscriber_id]
    
    async def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber from the hub."""
        async with self._lock:
            if subscriber_id in self._subscribers:
                del self._subscribers[subscriber_id]
                self.logger.debug(f"Subscriber {subscriber_id} unregistered")
    
    async def publish(self, beacon: Dict[str, Any]) -> None:
        """
        Broadcast a beacon to all subscribers.
        Non-blocking: drops message if subscriber queue is full.
        """
        async with self._lock:
            for sub_id, queue in self._subscribers.items():
                try:
                    queue.put_nowait(beacon.copy())
                except asyncio.QueueFull:
                    self.logger.warning(f"Queue full for {sub_id}, dropping beacon")


# =============================================================================
# HTTP CLIENT UTILITIES
# =============================================================================

async def http_request_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    payload: Optional[Dict] = None,
    logger: logging.Logger = None,
    max_retries: int = MAX_RETRIES
) -> Optional[Dict]:
    """
    Execute HTTP request with exponential backoff retry on failure.
    
    Args:
        session: aiohttp ClientSession
        method: HTTP method (GET, POST)
        url: Full URL to request
        payload: JSON payload for POST requests
        logger: Logger instance for logging
        max_retries: Maximum retry attempts
    
    Returns:
        Response JSON dict or None on failure
    """
    if logger is None:
        logger = logging.getLogger("HTTP")
    
    delay = INITIAL_RETRY_DELAY
    
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"GET {url} -> 200")
                        return data
                    else:
                        logger.warning(f"GET {url} -> {response.status}")
            
            elif method.upper() == "POST":
                async with session.post(url, json=payload) as response:
                    if response.status in (200, 201):
                        data = await response.json()
                        logger.info(f"POST {url} -> {response.status}")
                        return data
                    else:
                        text = await response.text()
                        logger.warning(f"POST {url} -> {response.status}: {text[:100]}")
        
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP error on attempt {attempt+1}/{max_retries}: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        if attempt < max_retries - 1:
            logger.debug(f"Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay * TIME_SCALE)
            delay *= 2  # Exponential backoff
    
    logger.error(f"Request to {url} failed after {max_retries} attempts")
    return None


# =============================================================================
# INFANT TAG DEVICE
# SSD Section 11.1 [cite: 2198]
# =============================================================================

@dataclass
class InfantTag:
    """
    Simulates an infant wristband/ankle tag that transmits BLE beacons.
    
    SSD Section 11.1 [cite: 2198]
    
    Beacon payload example:
        {
            "tag_uuid": "Infant_01",
            "timestamp": "2026-02-05T10:51:13+00:00",
            "battery": 85.5,
            "status": "NORMAL",
            "zone_id": "zone_3"
        }
    
    Tamper POST payload example:
        {
            "tag_uuid": "Infant_01",
            "timestamp": "2026-02-05T10:51:13+00:00",
            "zone_id": "zone_3",
            "battery": 85.5,
            "status": "TAMPER"
        }
    """
    
    uuid: str
    session: aiohttp.ClientSession
    beacon_hub: BeaconHub
    current_zone: str = "zone_1"
    battery_level: float = 100.0
    status: str = "NORMAL"  # "NORMAL" or "TAMPER"
    beacon_interval_base: float = 2.0
    _task: Optional[asyncio.Task] = field(default=None, repr=False, compare=False)
    _running: bool = field(default=False, repr=False, compare=False)
    
    def __post_init__(self):
        self.logger = logging.getLogger(f"InfantTag.{self.uuid}")
    
    def _get_timestamp(self) -> str:
        """Return current timestamp in ISO8601 format."""
        return datetime.now(timezone.utc).isoformat()
    
    def _build_beacon_payload(self) -> Dict[str, Any]:
        """Build beacon payload dict."""
        payload = {
            "tag_uuid": self.uuid,
            "timestamp": self._get_timestamp(),
            "battery": round(self.battery_level, 2),
            "status": self.status,
            "zone_id": self.current_zone
        }
        if self.battery_level <= 5.0:
            payload["battery_low"] = True
        return payload
    
    async def send_beacon(self) -> None:
        """Emit a beacon through the BeaconHub."""
        beacon = self._build_beacon_payload()
        await self.beacon_hub.publish(beacon)
        self.logger.info(f"Sent beacon to {self.current_zone} (battery: {self.battery_level:.1f}%)")
        
        # Battery drain
        drain = random.uniform(0.05, 0.2)
        self.battery_level = max(0.0, self.battery_level - drain)
        
        if self.battery_level <= 5.0:
            self.logger.warning(f"LOW BATTERY: {self.battery_level:.1f}%")
    
    async def trigger_tamper(self) -> None:
        """
        Trigger tamper event: set status to TAMPER, POST to backend, emit beacon.
        
        POST /infant/tamper
        Payload: { "tag_uuid": ..., "timestamp": ..., "zone_id": ..., "battery": ..., "status": "TAMPER" }
        """
        self.logger.warning(f"TAMPER TRIGGERED! Transitioning from {self.status} -> TAMPER")
        self.status = "TAMPER"
        
        payload = {
            "tag_uuid": self.uuid,
            "timestamp": self._get_timestamp(),
            "zone_id": self.current_zone,
            "battery": round(self.battery_level, 2),
            "status": "TAMPER"
        }
        
        url = f"{BACKEND_URL}/infant/tamper"
        result = await http_request_with_retry(
            self.session, "POST", url, payload, self.logger
        )
        
        if result:
            self.logger.info(f"Tamper event reported to backend: {result}")
        else:
            self.logger.error("Failed to report tamper event to backend")
        
        # Emit immediate beacon with TAMPER status
        await self.send_beacon()
    
    async def _movement_loop(self) -> None:
        """Periodically change zones to simulate infant movement."""
        while self._running:
            try:
                # Move every 5-15 seconds (scaled)
                wait_time = random.uniform(5, 15) * TIME_SCALE
                await asyncio.sleep(wait_time)
                
                # Choose a new zone (different from current)
                available_zones = [z for z in ZONES if z != self.current_zone]
                if available_zones:
                    old_zone = self.current_zone
                    self.current_zone = random.choice(available_zones)
                    self.logger.debug(f"Moved from {old_zone} to {self.current_zone}")
            
            except asyncio.CancelledError:
                break
    
    async def task_loop(self) -> None:
        """Main beacon transmission loop."""
        self._running = True
        self.logger.info(f"Started in {self.current_zone} with {self.battery_level:.1f}% battery")
        
        # Start movement task
        movement_task = asyncio.create_task(self._movement_loop())
        
        try:
            while self._running:
                await self.send_beacon()
                
                # Beacon interval with jitter
                jitter = random.uniform(-0.5, 0.5)
                interval = (self.beacon_interval_base + jitter) * TIME_SCALE
                await asyncio.sleep(max(0.1, interval))
        
        except asyncio.CancelledError:
            self.logger.debug("Task cancelled")
        finally:
            self._running = False
            movement_task.cancel()
            try:
                await movement_task
            except asyncio.CancelledError:
                pass
    
    def start(self) -> asyncio.Task:
        """Start the tag simulation task."""
        self._task = asyncio.create_task(self.task_loop())
        return self._task
    
    async def stop(self) -> None:
        """Stop the tag simulation."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# =============================================================================
# RTLS READER DEVICE
# SSD Section 11.2 [cite: 2202]
# =============================================================================

@dataclass
class RTLSReader:
    """
    Simulates an RTLS (Real-Time Location System) reader that "hears" beacons
    from infant tags and reports sightings to the backend.
    
    SSD Section 11.2 [cite: 2202]
    
    POST /rtls/readerEvent payload example:
        {
            "reader_id": "RTLS_01",
            "tag_uuid": "Infant_01",
            "timestamp": "2026-02-05T10:51:13+00:00",
            "zone_id": "zone_1",
            "rssi": -65
        }
    """
    
    reader_id: str
    assigned_zone_id: str
    session: aiohttp.ClientSession
    beacon_hub: BeaconHub
    adjacent_zones: List[str] = field(default_factory=list)
    _task: Optional[asyncio.Task] = field(default=None, repr=False, compare=False)
    _running: bool = field(default=False, repr=False, compare=False)
    _queue: Optional[asyncio.Queue] = field(default=None, repr=False, compare=False)
    
    def __post_init__(self):
        self.logger = logging.getLogger(f"RTLSReader.{self.reader_id}")
    
    def _can_hear_beacon(self, beacon_zone: str) -> bool:
        """
        Determine if reader can hear a beacon from given zone.
        Same zone: always hear. Adjacent zone: 70% probability.
        """
        if beacon_zone == self.assigned_zone_id:
            return True
        if beacon_zone in self.adjacent_zones:
            return random.random() < 0.7
        return False
    
    def _compute_rssi(self, beacon_zone: str) -> int:
        """
        Compute RSSI value based on zone proximity.
        Same zone: stronger signal (-40 to -60)
        Adjacent zone: weaker signal (-60 to -90)
        """
        if beacon_zone == self.assigned_zone_id:
            return random.randint(-60, -40)
        else:
            return random.randint(-90, -60)
    
    async def _report_sighting(self, beacon: Dict[str, Any], rssi: int) -> None:
        """Report a tag sighting to the backend."""
        payload = {
            "reader_id": self.reader_id,
            "tag_uuid": beacon["tag_uuid"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zone_id": self.assigned_zone_id,
            "rssi": rssi
        }
        
        url = f"{BACKEND_URL}/rtls/readerEvent"
        self.logger.debug(
            f"Sighting: {beacon['tag_uuid']} rssi={rssi}"
        )
        
        result = await http_request_with_retry(
            self.session, "POST", url, payload, self.logger
        )
        
        if result:
            self.logger.info(
                f"Forwarded sighting for {beacon['tag_uuid']} rssi={rssi}"
            )
    
    async def listen_loop(self) -> None:
        """Main loop: subscribe to beacons and process sightings."""
        self._running = True
        self._queue = await self.beacon_hub.subscribe(self.reader_id)
        self.logger.info(f"Started listening in {self.assigned_zone_id}")
        
        try:
            while self._running:
                try:
                    # Wait for beacon with timeout
                    beacon = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=5.0 * TIME_SCALE
                    )
                    
                    # Check if this reader can hear the beacon
                    beacon_zone = beacon.get("zone_id", "")
                    if self._can_hear_beacon(beacon_zone):
                        rssi = self._compute_rssi(beacon_zone)
                        await self._report_sighting(beacon, rssi)
                
                except asyncio.TimeoutError:
                    continue
        
        except asyncio.CancelledError:
            self.logger.debug("Task cancelled")
        finally:
            self._running = False
            await self.beacon_hub.unsubscribe(self.reader_id)
    
    def start(self) -> asyncio.Task:
        """Start the reader simulation task."""
        self._task = asyncio.create_task(self.listen_loop())
        return self._task
    
    async def stop(self) -> None:
        """Stop the reader simulation."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# =============================================================================
# GATE TERMINAL DEVICE
# SSD Section 11.3 [cite: 2206]
# =============================================================================

class GateTerminal:
    """
    Simulates a gate/exit terminal that authorizes mother-infant movement.
    Provides both interactive CLI and programmatic authorization methods.
    
    SSD Section 11.3 [cite: 2206]
    
    POST /gate/authorizeMovement payload example:
        {
            "infant_uuid": "Infant_01",
            "mother_uuid": "Mother_01",
            "staff_id": "Staff_001",
            "timestamp": "2026-02-05T10:51:13+00:00"
        }
    
    Response example:
        {
            "authorized": true,
            "reason": "Matching confirmed"
        }
    """
    
    def __init__(
        self,
        terminal_id: str,
        session: aiohttp.ClientSession,
        infant_uuids: List[str]
    ):
        self.terminal_id = terminal_id
        self.session = session
        self.infant_uuids = infant_uuids
        self.logger = logging.getLogger(f"GateTerminal.{terminal_id}")
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def authorize_movement(
        self,
        infant_uuid: str,
        mother_uuid: str,
        staff_id: str
    ) -> Dict[str, Any]:
        """
        Request movement authorization from the backend.
        
        Returns dict with 'authorized' (bool) and 'reason' (str) fields.
        """
        payload = {
            "infant_uuid": infant_uuid,
            "mother_uuid": mother_uuid,
            "staff_id": staff_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        url = f"{BACKEND_URL}/gate/authorizeMovement"
        self.logger.info(f"Requesting authorization for {infant_uuid}")
        
        result = await http_request_with_retry(
            self.session, "POST", url, payload, self.logger
        )
        
        if result:
            authorized = result.get("authorized", False)
            reason = result.get("reason", "Unknown")
            
            if authorized:
                self.logger.info(f"GATE OPEN for {infant_uuid}")
                print(f"\n[{self.terminal_id}] ✓ GATE OPEN - {infant_uuid}")
            else:
                self.logger.warning(f"ACCESS DENIED for {infant_uuid}: {reason}")
                print(f"\n[{self.terminal_id}] ✗ ACCESS DENIED: {reason}")
            
            return result
        else:
            self.logger.error("Authorization request failed")
            print(f"\n[{self.terminal_id}] ⚠ SYSTEM ERROR - Authorization unavailable")
            return {"authorized": False, "reason": "System error"}
    
    async def auto_test_authorization(self) -> Dict[str, Any]:
        """
        Automated test path for ScenarioRunner - non-interactive authorization test.
        """
        infant_uuid = self.infant_uuids[0] if self.infant_uuids else "Infant_01"
        mother_uuid = f"Mother_{infant_uuid.split('_')[1]}"
        staff_id = "Staff_AUTO_001"
        
        self.logger.info(f"Auto-test authorization for {infant_uuid}")
        return await self.authorize_movement(infant_uuid, mother_uuid, staff_id)
    
    async def _get_input_async(self, prompt: str, default: str = "") -> str:
        """Get user input without blocking the event loop."""
        loop = asyncio.get_event_loop()
        
        def _blocking_input():
            try:
                user_input = input(prompt)
                return user_input if user_input.strip() else default
            except EOFError:
                return default
        
        return await loop.run_in_executor(None, _blocking_input)
    
    async def interactive_loop(self) -> None:
        """
        Interactive CLI loop for gate authorization.
        Uses run_in_executor to avoid blocking the event loop.
        """
        self._running = True
        self.logger.info("Interactive gate terminal started")
        
        print(f"\n{'='*60}")
        print(f"Gate Terminal [{self.terminal_id}] - Interactive Mode")
        print(f"{'='*60}")
        print("Press Enter to authorize a movement, or type 'quit' to exit.\n")
        
        try:
            while self._running:
                try:
                    # Prompt for action
                    action = await asyncio.wait_for(
                        self._get_input_async("\n[Gate] Press Enter to scan or 'q' to quit: "),
                        timeout=30.0 * TIME_SCALE
                    )
                    
                    if action.lower() in ('q', 'quit', 'exit'):
                        break
                    
                    # Get infant UUID
                    default_infant = random.choice(self.infant_uuids) if self.infant_uuids else "Infant_01"
                    infant_uuid = await self._get_input_async(
                        f"Enter infant UUID [{default_infant}]: ",
                        default_infant
                    )
                    
                    # Get mother UUID
                    default_mother = f"Mother_{infant_uuid.split('_')[1] if '_' in infant_uuid else '01'}"
                    mother_uuid = await self._get_input_async(
                        f"Enter mother UUID [{default_mother}]: ",
                        default_mother
                    )
                    
                    # Get staff ID
                    staff_id = await self._get_input_async(
                        "Enter staff ID [Staff_001]: ",
                        "Staff_001"
                    )
                    
                    # Perform authorization
                    await self.authorize_movement(infant_uuid, mother_uuid, staff_id)
                
                except asyncio.TimeoutError:
                    continue
        
        except asyncio.CancelledError:
            self.logger.debug("Interactive loop cancelled")
        finally:
            self._running = False
            print(f"\n[{self.terminal_id}] Gate terminal shutting down...")
    
    def start(self) -> asyncio.Task:
        """Start the interactive terminal task."""
        self._task = asyncio.create_task(self.interactive_loop())
        return self._task
    
    async def stop(self) -> None:
        """Stop the terminal."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# =============================================================================
# ALARM NODE DEVICE
# SSD Section 11.4 [cite: 2209]
# =============================================================================

class AlarmNode:
    """
    Simulates an alarm/siren node that polls the backend for alarm status
    and activates when alerts are triggered.
    
    SSD Section 11.4 [cite: 2209]
    
    GET /alarms/status response example:
        {
            "alarm_active": true,
            "source": "Infant_01_TAMPER"
        }
    """
    
    def __init__(
        self,
        node_id: str,
        session: aiohttp.ClientSession,
        poll_interval: float = 5.0,
        ws_url: Optional[str] = None
    ):
        self.node_id = node_id
        self.session = session
        self.poll_interval = poll_interval
        self.ws_url = ws_url
        self.logger = logging.getLogger(f"AlarmNode.{node_id}")
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alarm_active = False
    
    async def poll_alarm_status(self) -> None:
        """Poll the backend for current alarm status."""
        url = f"{BACKEND_URL}/alarms/status"
        
        result = await http_request_with_retry(
            self.session, "GET", url, logger=self.logger
        )
        
        if result:
            alarm_active = result.get("alarm_active", False)
            source = result.get("source", "unknown")
            
            if alarm_active and not self._alarm_active:
                # Alarm just activated
                self._alarm_active = True
                self.logger.warning(f"SIREN ACTIVE (source: {source})")
                print(f"\n[{self.node_id}] 🚨 SIREN ACTIVE (source: {source})")
            
            elif not alarm_active and self._alarm_active:
                # Alarm cleared
                self._alarm_active = False
                self.logger.info("Alarm cleared")
                print(f"\n[{self.node_id}] ✓ Alarm cleared")
            
            else:
                self.logger.debug(f"Alarm status: active={alarm_active}")
    
    async def poll_loop(self) -> None:
        """Main polling loop for alarm status."""
        self._running = True
        self.logger.info(f"Started polling every {self.poll_interval}s")
        
        try:
            while self._running:
                await self.poll_alarm_status()
                await asyncio.sleep(self.poll_interval * TIME_SCALE)
        
        except asyncio.CancelledError:
            self.logger.debug("Poll loop cancelled")
        finally:
            self._running = False
    
    async def websocket_loop(self) -> None:
        """
        Optional WebSocket listener for real-time alarm updates.
        Connects to ws_url if provided.
        """
        if not self.ws_url:
            return
        
        self.logger.info(f"Connecting to WebSocket: {self.ws_url}")
        
        try:
            async with self.session.ws_connect(self.ws_url) as ws:
                self.logger.info("WebSocket connected")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("alarm_active"):
                            source = data.get("source", "unknown")
                            self.logger.warning(f"WS: SIREN ACTIVE ({source})")
                            print(f"\n[{self.node_id}] 🚨 WS ALERT: {source}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
    
    def start(self) -> asyncio.Task:
        """Start the alarm node polling task."""
        self._task = asyncio.create_task(self.poll_loop())
        return self._task
    
    async def stop(self) -> None:
        """Stop the alarm node."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# =============================================================================
# BIOMETRIC SCANNER DEVICE
# =============================================================================

class BiometricScanner:
    """
    Simulates a biometric scanner for infant enrollment.
    Generates dummy biometric templates and submits to backend.
    
    POST /biometric/enrollInfant payload example:
        {
            "infant_uuid": "Infant_01",
            "template_base64": "ZHVtbXktdGVtcGxhdGUtSW5mYW50XzAx"
        }
    """
    
    def __init__(self, scanner_id: str, session: aiohttp.ClientSession):
        self.scanner_id = scanner_id
        self.session = session
        self.logger = logging.getLogger(f"BiometricScanner.{scanner_id}")
    
    def _generate_template(self, infant_uuid: str) -> str:
        """Generate a dummy biometric template as base64."""
        template_data = f"dummy-template-{infant_uuid}".encode()
        return base64.b64encode(template_data).decode()
    
    async def enroll_infant(self, infant_uuid: str) -> Dict[str, Any]:
        """
        Enroll an infant with a dummy biometric template.
        
        Returns enrollment result from backend.
        """
        template = self._generate_template(infant_uuid)
        
        payload = {
            "infant_uuid": infant_uuid,
            "template_base64": template
        }
        
        url = f"{BACKEND_URL}/biometric/enrollInfant"
        self.logger.info(f"Enrolling {infant_uuid}")
        
        result = await http_request_with_retry(
            self.session, "POST", url, payload, self.logger
        )
        
        if result:
            self.logger.info(f"Enrollment successful for {infant_uuid}: {result}")
            return result
        else:
            self.logger.error(f"Enrollment failed for {infant_uuid}")
            return {"success": False, "error": "Enrollment failed"}


# =============================================================================
# SCENARIO RUNNER
# =============================================================================

class ScenarioRunner:
    """
    Orchestrates simulation scenarios including:
    - Triggering tamper events after delay
    - Running biometric enrollment tests
    - Executing gate authorization tests
    """
    
    def __init__(
        self,
        infant_tags: Dict[str, InfantTag],
        gate_terminal: GateTerminal,
        biometric_scanner: BiometricScanner
    ):
        self.infant_tags = infant_tags
        self.gate_terminal = gate_terminal
        self.biometric_scanner = biometric_scanner
        self.logger = logging.getLogger("ScenarioRunner")
    
    async def run_scenarios(self) -> None:
        """Run all test scenarios."""
        self.logger.info("Scenario runner started")
        
        try:
            # Wait 3 seconds then run gate authorization test
            await asyncio.sleep(3.0 * TIME_SCALE)
            self.logger.info("Running gate authorization auto-test...")
            await self.gate_terminal.auto_test_authorization()
            
            # Wait until 10 seconds from start, then trigger tamper
            await asyncio.sleep(7.0 * TIME_SCALE)  # 3 + 7 = 10 seconds
            
            # Trigger tamper on Infant_01
            if "Infant_01" in self.infant_tags:
                self.logger.info("Triggering tamper event on Infant_01...")
                await self.infant_tags["Infant_01"].trigger_tamper()
            else:
                self.logger.warning("Infant_01 not found, skipping tamper test")
            
            # Run biometric enrollment for Infant_01
            self.logger.info("Running biometric enrollment for Infant_01...")
            await self.biometric_scanner.enroll_infant("Infant_01")
            
            self.logger.info("All scenarios completed")
        
        except asyncio.CancelledError:
            self.logger.info("Scenario runner cancelled")


# =============================================================================
# MAIN SIMULATION
# =============================================================================

async def main():
    """
    Main entry point for the IoT simulation.
    
    Creates and orchestrates all simulated devices:
    - 50 InfantTag instances
    - 10 RTLSReader instances
    - 1 GateTerminal (interactive)
    - 1 AlarmNode
    - 1 BiometricScanner
    - 1 ScenarioRunner
    """
    logger = logging.getLogger("Main")
    
    print("=" * 70)
    print("INFANT SECURITY IoT SIMULATION SUITE")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Infant Tags: {NUM_INFANTS}")
    print(f"RTLS Readers: {NUM_READERS}")
    print(f"Zones: {NUM_ZONES}")
    print(f"Fast Mode: {FAST_MODE}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print("=" * 70 + "\n")
    
    logger.info("Initializing simulation...")
    
    # Create aiohttp session
    timeout = aiohttp.ClientTimeout(total=30)
    session = aiohttp.ClientSession(timeout=timeout)
    
    # Create BeaconHub
    beacon_hub = BeaconHub()
    
    # Track all tasks for cleanup
    tasks: List[asyncio.Task] = []
    infant_tags: Dict[str, InfantTag] = {}
    readers: List[RTLSReader] = []
    
    try:
        # Create InfantTag instances
        logger.info(f"Creating {NUM_INFANTS} infant tags...")
        for i in range(1, NUM_INFANTS + 1):
            uuid = f"Infant_{i:02d}"
            tag = InfantTag(
                uuid=uuid,
                session=session,
                beacon_hub=beacon_hub,
                current_zone=random.choice(ZONES),
                battery_level=random.uniform(60.0, 100.0),
                status="NORMAL"
            )
            infant_tags[uuid] = tag
            tasks.append(tag.start())
        
        # Create RTLSReader instances with zone assignments
        logger.info(f"Creating {NUM_READERS} RTLS readers...")
        for i in range(1, NUM_READERS + 1):
            reader_id = f"RTLS_{i:02d}"
            # Round-robin zone assignment
            zone_index = (i - 1) % len(ZONES)
            assigned_zone = ZONES[zone_index]
            
            # Define adjacent zones (simple: previous and next)
            adjacent = []
            if zone_index > 0:
                adjacent.append(ZONES[zone_index - 1])
            if zone_index < len(ZONES) - 1:
                adjacent.append(ZONES[zone_index + 1])
            
            reader = RTLSReader(
                reader_id=reader_id,
                assigned_zone_id=assigned_zone,
                session=session,
                beacon_hub=beacon_hub,
                adjacent_zones=adjacent
            )
            readers.append(reader)
            tasks.append(reader.start())
        
        # Create GateTerminal (interactive)
        infant_uuids = list(infant_tags.keys())
        gate_terminal = GateTerminal(
            terminal_id="Gate_01",
            session=session,
            infant_uuids=infant_uuids
        )
        tasks.append(gate_terminal.start())
        
        # Create AlarmNode
        alarm_node = AlarmNode(
            node_id="Alarm_01",
            session=session,
            poll_interval=5.0
        )
        tasks.append(alarm_node.start())
        
        # Create BiometricScanner
        biometric_scanner = BiometricScanner(
            scanner_id="Bio_01",
            session=session
        )
        
        # Create and start ScenarioRunner
        scenario_runner = ScenarioRunner(
            infant_tags=infant_tags,
            gate_terminal=gate_terminal,
            biometric_scanner=biometric_scanner
        )
        scenario_task = asyncio.create_task(scenario_runner.run_scenarios())
        tasks.append(scenario_task)
        
        logger.info("All devices started. Simulation running...")
        logger.info("Press Ctrl+C to stop the simulation.\n")
        
        # Setup signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler(sig):
            logger.info(f"Received signal {sig.name}, initiating shutdown...")
            shutdown_event.set()
        
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, partial(signal_handler, sig))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass
        
        # Wait for shutdown signal or run forever
        try:
            await shutdown_event.wait()
        except asyncio.CancelledError:
            pass
    
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise
    
    finally:
        # Graceful shutdown
        logger.info("Shutting down simulation...")
        
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop individual devices
        for tag in infant_tags.values():
            await tag.stop()
        for reader in readers:
            await reader.stop()
        
        # Close aiohttp session
        await session.close()
        
        # Allow time for cleanup
        await asyncio.sleep(0.5)
        
        logger.info("Simulation stopped.")
        print("\n" + "=" * 70)
        print("SIMULATION ENDED")
        print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    except Exception as e:
        print(f"\nSimulation failed: {e}")
        sys.exit(1)
