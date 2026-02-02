import { useState, useEffect, useRef } from "react";
import {
  createWebSocketConnection,
  createGateEventsWebSocket,
  createAlertsWebSocket,
  fetchRTLSPositions,
  fetchAlerts,
  fetchGateEvents,
} from "../api";
import type { RTLSPosition, GateEvent, Alert, WSMessage } from "../types";

export function usePositionTracker(floorId?: string) {
  const [positions, setPositions] = useState<RTLSPosition[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const positionsMap = useRef<Map<string, RTLSPosition>>(new Map());

  // Initial fetch (still useful as fallback or before WS connect)
  useEffect(() => {
    fetchRTLSPositions({ floor: floorId })
      .then((initialPositions) => {
        initialPositions.forEach((p) => positionsMap.current.set(p.tagId, p));
        setPositions(Array.from(positionsMap.current.values()));
      })
      .catch(console.error);
  }, [floorId]);

  // WebSocket connection
  useEffect(() => {
    const ws = createWebSocketConnection(
      (message: WSMessage) => {
        if (message.type === "initial" && message.positions) {
          message.positions.forEach((p) => {
            if (!floorId || p.floor === floorId) {
              positionsMap.current.set(p.tagId, p);
            }
          });
          setPositions(Array.from(positionsMap.current.values()));
        } else if (message.type === "position" && message.data) {
          const pos = message.data as RTLSPosition;
          if (!floorId || pos.floor === floorId) {
            positionsMap.current.set(pos.tagId, pos);
            // Debounce updates slightly if needed, or update immediately for smoothness
            setPositions(Array.from(positionsMap.current.values()));
          }
        }
      },
      () => setIsConnected(false),
      () => setIsConnected(false),
    );

    ws.onopen = () => setIsConnected(true);

    return () => {
      ws.close();
    };
  }, [floorId]);

  return { positions, isConnected };
}

export function useGateEvents() {
  const [events, setEvents] = useState<GateEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Initial fetch
  useEffect(() => {
    fetchGateEvents()
      .then((response) => {
        setEvents(response.items || []);
      })
      .catch(console.error);
  }, []);

  // WebSocket connection
  useEffect(() => {
    const ws = createGateEventsWebSocket(
      (message: WSMessage) => {
        if (message.type === "event" && message.data) {
          const event = message.data as GateEvent;
          setEvents((prev) => [event, ...prev].slice(0, 50)); // Keep last 50 events
        }
        // Note: 'initial' type for Gates WS returns 'gates' state, not events history.
        // We ignore it here as we fetched events history via API.
      },
      () => setIsConnected(false),
    );

    ws.onopen = () => setIsConnected(true);

    return () => {
      ws.close();
    };
  }, []);

  return { events, isConnected };
}

export function useAlertTracker() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Initial fetch
  useEffect(() => {
    fetchAlerts({ acknowledged: false })
      .then((initialAlerts) => {
        setAlerts(initialAlerts);
      })
      .catch(console.error);
  }, []);

  // WebSocket connection
  useEffect(() => {
    const ws = createAlertsWebSocket(
      (message: WSMessage) => {
        if (message.type === "initial" && message.alerts) {
          // Replace alerts with active ones from server
          setAlerts(message.alerts);
        } else if (message.type === "alert" && message.data) {
          const alert = message.data as Alert;
          setAlerts((prev) => {
            const exists = prev.find((a) => a.alertId === alert.alertId); // Assuming alertId is unique
            if (exists) {
              return prev.map((a) => (a.alertId === alert.alertId ? alert : a));
            }
            return [alert, ...prev];
          });
        }
      },
      () => setIsConnected(false),
    );

    ws.onopen = () => setIsConnected(true);

    return () => {
      ws.close();
    };
  }, []);

  return { alerts, setAlerts, isConnected };
}
