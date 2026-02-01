"""
WebSocket endpoints for real-time streaming.

Provides WebSocket connections for RTLS positions, gate events, and alerts.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_libraries.database import get_db
from shared_libraries.logging import get_logger
from database.orm_models.models import RTLSPosition, Gate, GateEvent, Alert

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time streaming."""
    
    def __init__(self):
        # Connections grouped by channel
        self.position_connections: Set[WebSocket] = set()
        self.gate_connections: Set[WebSocket] = set()
        self.alert_connections: Set[WebSocket] = set()
    
    async def connect_positions(self, websocket: WebSocket):
        await websocket.accept()
        self.position_connections.add(websocket)
        logger.info("websocket_connected", channel="positions", total=len(self.position_connections))
    
    async def connect_gates(self, websocket: WebSocket):
        await websocket.accept()
        self.gate_connections.add(websocket)
        logger.info("websocket_connected", channel="gates", total=len(self.gate_connections))
    
    async def connect_alerts(self, websocket: WebSocket):
        await websocket.accept()
        self.alert_connections.add(websocket)
        logger.info("websocket_connected", channel="alerts", total=len(self.alert_connections))
    
    def disconnect_positions(self, websocket: WebSocket):
        self.position_connections.discard(websocket)
        logger.info("websocket_disconnected", channel="positions", total=len(self.position_connections))
    
    def disconnect_gates(self, websocket: WebSocket):
        self.gate_connections.discard(websocket)
        logger.info("websocket_disconnected", channel="gates", total=len(self.gate_connections))
    
    def disconnect_alerts(self, websocket: WebSocket):
        self.alert_connections.discard(websocket)
        logger.info("websocket_disconnected", channel="alerts", total=len(self.alert_connections))
    
    async def broadcast_positions(self, data: dict):
        """Broadcast position data to all connected clients."""
        if not self.position_connections:
            return
        
        message = json.dumps(data, default=str)
        for connection in list(self.position_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.position_connections.discard(connection)
    
    async def broadcast_gates(self, data: dict):
        """Broadcast gate event to all connected clients."""
        if not self.gate_connections:
            return
        
        message = json.dumps(data, default=str)
        for connection in list(self.gate_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.gate_connections.discard(connection)
    
    async def broadcast_alerts(self, data: dict):
        """Broadcast alert to all connected clients."""
        if not self.alert_connections:
            return
        
        message = json.dumps(data, default=str)
        for connection in list(self.alert_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.alert_connections.discard(connection)


# Global connection manager instance
manager = ConnectionManager()


# =============================================================================
# Helper Functions
# =============================================================================

def serialize_position(pos: RTLSPosition) -> dict:
    """Serialize an RTLS position for JSON transmission."""
    return {
        "id": str(pos.id),
        "tagId": pos.tag_id,
        "assetType": pos.asset_type,
        "x": pos.x,
        "y": pos.y,
        "z": pos.z,
        "floor": pos.floor,
        "accuracy": pos.accuracy,
        "batteryPct": pos.battery_pct,
        "gatewayId": pos.gateway_id,
        "rssi": pos.rssi,
        "timestamp": pos.timestamp.isoformat() if pos.timestamp else None,
    }


def serialize_gate(gate: Gate) -> dict:
    """Serialize a gate for JSON transmission."""
    return {
        "id": str(gate.id),
        "gateId": gate.gate_id,
        "name": gate.name,
        "floor": gate.floor,
        "zone": gate.zone,
        "state": gate.state.value if gate.state else None,
        "lastStateChange": gate.last_state_change.isoformat() if gate.last_state_change else None,
        "cameraId": gate.camera_id,
    }


def serialize_alert(alert: Alert) -> dict:
    """Serialize an alert for JSON transmission."""
    return {
        "id": str(alert.id),
        "alertType": alert.alert_type,
        "severity": alert.severity.value if alert.severity else None,
        "message": alert.message,
        "tagId": alert.tag_id,
        "acknowledged": alert.acknowledged,
        "createdAt": alert.created_at.isoformat() if alert.created_at else None,
    }


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/positions/live")
async def websocket_positions(
    websocket: WebSocket,
    floor: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for streaming live RTLS positions.
    
    Clients receive position updates every second.
    Filter by floor using query param: ?floor=F1
    """
    await manager.connect_positions(websocket)
    
    try:
        # Send initial positions
        async for db in get_db():
            query = select(RTLSPosition).order_by(RTLSPosition.timestamp.desc()).limit(100)
            if floor:
                query = query.where(RTLSPosition.floor == floor)
            
            result = await db.execute(query)
            positions = result.scalars().all()
            
            initial_data = {
                "type": "initial",
                "positions": [serialize_position(p) for p in positions],
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_text(json.dumps(initial_data, default=str))
            break
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client message (ping/pong or subscription changes)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                }))
    
    except WebSocketDisconnect:
        manager.disconnect_positions(websocket)
    except Exception as e:
        logger.error("websocket_error", channel="positions", error=str(e))
        manager.disconnect_positions(websocket)


@router.websocket("/gates/events")
async def websocket_gate_events(websocket: WebSocket):
    """
    WebSocket endpoint for streaming gate events.
    
    Clients receive gate state changes and access events in real-time.
    """
    await manager.connect_gates(websocket)
    
    try:
        # Send current gate states
        async for db in get_db():
            result = await db.execute(select(Gate))
            gates = result.scalars().all()
            
            initial_data = {
                "type": "initial",
                "gates": [serialize_gate(g) for g in gates],
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_text(json.dumps(initial_data, default=str))
            break
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                if data == "ping":
                    await websocket.send_text("pong")
                
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                }))
    
    except WebSocketDisconnect:
        manager.disconnect_gates(websocket)
    except Exception as e:
        logger.error("websocket_error", channel="gates", error=str(e))
        manager.disconnect_gates(websocket)


@router.websocket("/alerts/live")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for streaming alerts.
    
    Clients receive new and updated alerts in real-time.
    """
    await manager.connect_alerts(websocket)
    
    try:
        # Send current active alerts
        async for db in get_db():
            result = await db.execute(
                select(Alert)
                .where(Alert.acknowledged == False)
                .order_by(Alert.created_at.desc())
                .limit(50)
            )
            alerts = result.scalars().all()
            
            initial_data = {
                "type": "initial",
                "alerts": [serialize_alert(a) for a in alerts],
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_text(json.dumps(initial_data, default=str))
            break
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                if data == "ping":
                    await websocket.send_text("pong")
                
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                }))
    
    except WebSocketDisconnect:
        manager.disconnect_alerts(websocket)
    except Exception as e:
        logger.error("websocket_error", channel="alerts", error=str(e))
        manager.disconnect_alerts(websocket)


# =============================================================================
# Broadcast Functions (to be called by other services)
# =============================================================================

async def broadcast_position_update(position: dict):
    """Broadcast a new position update to all connected clients."""
    await manager.broadcast_positions({
        "type": "position",
        "data": position,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_gate_event(event: dict):
    """Broadcast a gate event to all connected clients."""
    await manager.broadcast_gates({
        "type": "event",
        "data": event,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_alert(alert: dict):
    """Broadcast a new or updated alert to all connected clients."""
    await manager.broadcast_alerts({
        "type": "alert",
        "data": alert,
        "timestamp": datetime.utcnow().isoformat(),
    })
