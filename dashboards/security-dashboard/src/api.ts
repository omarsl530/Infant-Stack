import type {
  RTLSPosition,
  RTLSTag,
  Gate,
  GateEvent,
  Alert,
  Zone,
  Camera,
  Floorplan,
  PaginatedResponse,
} from './types';

const API_BASE = '/api/v1';

// =============================================================================
// Helper Functions
// =============================================================================

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

// =============================================================================
// RTLS API
// =============================================================================

export async function fetchRTLSTags(): Promise<RTLSTag[]> {
  return fetchJSON<RTLSTag[]>(`${API_BASE}/rtls/tags`);
}

export async function fetchRTLSPositions(params?: {
  floor?: string;
  tagIds?: string[];
  from?: string;
  to?: string;
}): Promise<RTLSPosition[]> {
  const searchParams = new URLSearchParams();
  if (params?.floor) searchParams.set('floor', params.floor);
  if (params?.from) searchParams.set('from', params.from);
  if (params?.to) searchParams.set('to', params.to);
  if (params?.tagIds) searchParams.set('tagIds', params.tagIds.join(','));

  return fetchJSON<RTLSPosition[]>(`${API_BASE}/rtls/positions?${searchParams}`);
}

export async function fetchTagHistory(
  tagId: string,
  from: string,
  to: string
): Promise<RTLSPosition[]> {
  return fetchJSON<RTLSPosition[]>(
    `${API_BASE}/rtls/positions/history?tagId=${tagId}&from=${from}&to=${to}`
  );
}

// =============================================================================
// Gates API
// =============================================================================

export async function fetchGates(): Promise<Gate[]> {
  return fetchJSON<Gate[]>(`${API_BASE}/gates`);
}

export async function fetchGateEvents(params?: {
  gateId?: string;
  from?: string;
  to?: string;
  eventType?: string;
}): Promise<PaginatedResponse<GateEvent>> {
  const searchParams = new URLSearchParams();
  if (params?.gateId) searchParams.set('gateId', params.gateId);
  if (params?.from) searchParams.set('from', params.from);
  if (params?.to) searchParams.set('to', params.to);
  if (params?.eventType) searchParams.set('eventType', params.eventType);

  return fetchJSON<PaginatedResponse<GateEvent>>(`${API_BASE}/gates/events?${searchParams}`);
}

export async function controlGate(gateId: string, action: 'lock' | 'unlock'): Promise<void> {
  await fetchJSON(`${API_BASE}/gates/${gateId}/control`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

// =============================================================================
// Alerts API
// =============================================================================

export async function fetchAlerts(params?: {
  severity?: string;
  acknowledged?: boolean;
  from?: string;
  to?: string;
}): Promise<Alert[]> {
  const searchParams = new URLSearchParams();
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.acknowledged !== undefined) searchParams.set('acknowledged', String(params.acknowledged));
  if (params?.from) searchParams.set('from', params.from);
  if (params?.to) searchParams.set('to', params.to);

  return fetchJSON<Alert[]>(`${API_BASE}/alerts?${searchParams}`);
}

export async function acknowledgeAlert(alertId: string): Promise<void> {
  await fetchJSON(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
}

export async function dismissAlert(alertId: string): Promise<void> {
  await fetchJSON(`${API_BASE}/alerts/${alertId}/dismiss`, {
    method: 'POST',
  });
}

export async function escalateAlert(alertId: string): Promise<void> {
  await fetchJSON(`${API_BASE}/alerts/${alertId}/escalate`, {
    method: 'POST',
  });
}

// =============================================================================
// Zones API
// =============================================================================

export async function fetchZones(floor?: string): Promise<Zone[]> {
  const params = floor ? `?floor=${floor}` : '';
  return fetchJSON<Zone[]>(`${API_BASE}/zones${params}`);
}

// =============================================================================
// Cameras API
// =============================================================================

export async function fetchCameras(): Promise<Camera[]> {
  return fetchJSON<Camera[]>(`${API_BASE}/cameras`);
}

export async function getCameraSnapshot(cameraId: string): Promise<string> {
  const response = await fetch(`${API_BASE}/cameras/${cameraId}/snapshot`);
  if (!response.ok) throw new Error('Failed to get camera snapshot');
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// =============================================================================
// Floorplans API
// =============================================================================

export async function fetchFloorplans(): Promise<Floorplan[]> {
  return fetchJSON<Floorplan[]>(`${API_BASE}/floorplans`);
}

// =============================================================================
// Dashboard Stats API
// =============================================================================

export interface DashboardStats {
  totalTags: number;
  activeTags: number;
  alertsCount: number;
  criticalAlerts: number;
  gatesCount: number;
  gatesOpen: number;
  accessEventsToday: number;
  deniedAccessToday: number;
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return fetchJSON<DashboardStats>(`${API_BASE}/dashboard/stats`);
}

// =============================================================================
// WebSocket Connection
// =============================================================================

export type WSEventType = 'rtls.position' | 'gate.event' | 'alert.new' | 'alert.update';

export interface WSMessage {
  type: WSEventType;
  data: RTLSPosition | GateEvent | Alert;
  timestamp: string;
}

export function createWebSocketConnection(
  onMessage: (message: WSMessage) => void,
  onError?: (error: Event) => void,
  onClose?: (event: CloseEvent) => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const ws = new WebSocket(`${protocol}//${host}/ws/security`);

  ws.onmessage = (event) => {
    try {
      const message: WSMessage = JSON.parse(event.data);
      onMessage(message);
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  };

  ws.onerror = (event) => {
    console.error('WebSocket error:', event);
    onError?.(event);
  };

  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
    onClose?.(event);
  };

  return ws;
}

// =============================================================================
// Server-Sent Events Connection
// =============================================================================

export function createSSEConnection(
  onMessage: (message: WSMessage) => void,
  onError?: (error: Event) => void
): EventSource {
  const eventSource = new EventSource(`${API_BASE}/events/stream`);

  eventSource.onmessage = (event) => {
    try {
      const message: WSMessage = JSON.parse(event.data);
      onMessage(message);
    } catch (err) {
      console.error('Failed to parse SSE message:', err);
    }
  };

  eventSource.onerror = (event) => {
    console.error('SSE error:', event);
    onError?.(event);
  };

  return eventSource;
}
