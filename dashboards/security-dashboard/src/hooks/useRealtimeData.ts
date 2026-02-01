import { useState, useEffect, useCallback, useRef } from 'react';
import type { RTLSPosition, Alert, GateEvent } from '../types';
import { createWebSocketConnection, type WSMessage } from '../api';

interface UseRealtimeDataOptions {
  onPositionUpdate?: (position: RTLSPosition) => void;
  onGateEvent?: (event: GateEvent) => void;
  onAlert?: (alert: Alert) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseRealtimeDataReturn {
  isConnected: boolean;
  lastUpdate: Date | null;
  connectionError: string | null;
  reconnect: () => void;
}

export function useRealtimeData(options: UseRealtimeDataOptions = {}): UseRealtimeDataReturn {
  const {
    onPositionUpdate,
    onGateEvent,
    onAlert,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const handleMessage = useCallback((message: WSMessage) => {
    setLastUpdate(new Date());
    
    switch (message.type) {
      case 'rtls.position':
        onPositionUpdate?.(message.data as RTLSPosition);
        break;
      case 'gate.event':
        onGateEvent?.(message.data as GateEvent);
        break;
      case 'alert.new':
      case 'alert.update':
        onAlert?.(message.data as Alert);
        break;
    }
  }, [onPositionUpdate, onGateEvent, onAlert]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionError(null);
    
    wsRef.current = createWebSocketConnection(
      handleMessage,
      () => {
        setIsConnected(false);
        setConnectionError('Connection error');
      },
      (event) => {
        setIsConnected(false);
        
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else {
          setConnectionError(`Connection closed: ${event.reason || 'Unknown reason'}`);
        }
      }
    );

    wsRef.current.onopen = () => {
      setIsConnected(true);
      setConnectionError(null);
      reconnectAttemptsRef.current = 0;
    };
  }, [handleMessage, reconnectInterval, maxReconnectAttempts]);

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    lastUpdate,
    connectionError,
    reconnect,
  };
}

// =============================================================================
// Position Tracking Hook
// =============================================================================

export function usePositionTracker(floor?: string) {
  const [positions, setPositions] = useState<Map<string, RTLSPosition>>(new Map());

  const handlePositionUpdate = useCallback((position: RTLSPosition) => {
    if (floor && position.floor !== floor) return;
    
    setPositions((prev) => {
      const next = new Map(prev);
      next.set(position.tagId, position);
      return next;
    });
  }, [floor]);

  const { isConnected, lastUpdate, connectionError, reconnect } = useRealtimeData({
    onPositionUpdate: handlePositionUpdate,
  });

  return {
    positions: Array.from(positions.values()),
    positionsMap: positions,
    isConnected,
    lastUpdate,
    connectionError,
    reconnect,
  };
}

// =============================================================================
// Alert Tracker Hook
// =============================================================================

export function useAlertTracker() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [newAlertCount, setNewAlertCount] = useState(0);

  const handleAlert = useCallback((alert: Alert) => {
    setAlerts((prev) => {
      const existingIndex = prev.findIndex((a) => a.alertId === alert.alertId);
      if (existingIndex >= 0) {
        // Update existing alert
        const updated = [...prev];
        updated[existingIndex] = alert;
        return updated;
      }
      // Add new alert at the beginning
      setNewAlertCount((c) => c + 1);
      return [alert, ...prev];
    });
  }, []);

  const { isConnected, lastUpdate, connectionError, reconnect } = useRealtimeData({
    onAlert: handleAlert,
  });

  const clearNewAlertCount = useCallback(() => {
    setNewAlertCount(0);
  }, []);

  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.alertId === alertId ? { ...a, acknowledged: true, acknowledgedAt: new Date().toISOString() } : a
      )
    );
  }, []);

  const dismissAlert = useCallback((alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.alertId !== alertId));
  }, []);

  return {
    alerts,
    newAlertCount,
    clearNewAlertCount,
    acknowledgeAlert,
    dismissAlert,
    isConnected,
    lastUpdate,
    connectionError,
    reconnect,
  };
}

// =============================================================================
// Gate Events Hook
// =============================================================================

export function useGateEvents() {
  const [events, setEvents] = useState<GateEvent[]>([]);
  const maxEvents = 100;

  const handleGateEvent = useCallback((event: GateEvent) => {
    setEvents((prev) => {
      const next = [event, ...prev];
      return next.slice(0, maxEvents);
    });
  }, []);

  const { isConnected, lastUpdate, connectionError, reconnect } = useRealtimeData({
    onGateEvent: handleGateEvent,
  });

  return {
    events,
    isConnected,
    lastUpdate,
    connectionError,
    reconnect,
  };
}
