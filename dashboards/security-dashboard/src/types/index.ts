// =============================================================================
// RTLS Types
// =============================================================================

export interface RTLSPosition {
  tagId: string;
  assetType: 'infant' | 'mother' | 'staff' | 'equipment';
  x: number;
  y: number;
  z: number;
  floor: string;
  accuracy: number;
  batteryPct: number;
  gatewayId: string;
  rssi: number;
  timestamp: string;
  sequenceId: number;
}

export interface RTLSTag {
  id: string;
  tagId: string;
  name: string;
  assetType: 'infant' | 'mother' | 'staff' | 'equipment';
  status: 'active' | 'inactive' | 'alert' | 'low_battery';
  lastPosition: RTLSPosition | null;
  assignedTo?: string;
}

// =============================================================================
// Gate & Access Types
// =============================================================================

export type GateState = 'OPEN' | 'CLOSED' | 'FORCED_OPEN' | 'HELD_OPEN' | 'UNKNOWN';

export interface Gate {
  id: string;
  gateId: string;
  name: string;
  floor: string;
  zone: string;
  state: GateState;
  lastStateChange: string;
  cameraId?: string;
  cameraUrl?: string;
}

export interface GateEvent {
  id: string;
  eventType: 'badgeScan' | 'gateState' | 'forced' | 'heldOpen';
  timestamp: string;
  gateId: string;
  gateName: string;
  state?: GateState;
  previousState?: GateState;
  durationMs?: number;
  badgeId?: string;
  userId?: string;
  userName?: string;
  result?: 'GRANTED' | 'DENIED' | 'TIMEOUT';
  direction?: 'IN' | 'OUT';
}

export interface BadgeScan {
  id: string;
  timestamp: string;
  gateId: string;
  gateName: string;
  badgeId: string;
  userId: string;
  userName: string;
  result: 'GRANTED' | 'DENIED';
  direction: 'IN' | 'OUT';
  floor: string;
}

// =============================================================================
// Alert Types
// =============================================================================

export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertType = 
  | 'DOOR_FORCED_OPEN'
  | 'DOOR_HELD_OPEN'
  | 'GEOFENCE_BREACH'
  | 'TAG_NO_UPDATE'
  | 'TAG_LOW_BATTERY'
  | 'UNAUTHORIZED_ACCESS'
  | 'PAIRING_MISMATCH'
  | 'SYSTEM_ERROR';

export interface Alert {
  id: string;
  alertId: string;
  type: AlertType;
  severity: AlertSeverity;
  timestamp: string;
  entityType: 'gate' | 'tag' | 'zone' | 'system';
  entityId: string;
  tagId?: string;
  message: string;
  metadata?: Record<string, unknown>;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  escalatedAt?: string;
}

// =============================================================================
// Zone & Geofence Types
// =============================================================================

export interface Zone {
  id: string;
  name: string;
  floor: string;
  type: 'authorized' | 'restricted' | 'exit' | 'entrance';
  polygon: { x: number; y: number }[];
  color: string;
}

export interface Geofence {
  id: string;
  name: string;
  zoneId: string;
  ruleType: 'enter' | 'exit' | 'dwell';
  tagFilter?: string[];
  alertSeverity: AlertSeverity;
  enabled: boolean;
}

// =============================================================================
// Camera Types
// =============================================================================

export interface Camera {
  id: string;
  cameraId: string;
  name: string;
  gateId?: string;
  zone?: string;
  floor: string;
  streamUrl: string;
  thumbnailUrl: string;
  status: 'online' | 'offline' | 'error';
}

// =============================================================================
// Floorplan Types
// =============================================================================

export interface Floorplan {
  id: string;
  floor: string;
  name: string;
  imageUrl: string;
  width: number;
  height: number;
  scale: number; // pixels per meter
  originX: number;
  originY: number;
}

// =============================================================================
// Dashboard State Types
// =============================================================================

export interface DashboardFilters {
  floor: string;
  zone?: string;
  assetType?: RTLSTag['assetType'];
  alertSeverity?: AlertSeverity;
  timeRange: {
    from: Date;
    to: Date;
  };
}

export interface PlaybackState {
  isPlaying: boolean;
  isLive: boolean;
  currentTime: Date;
  playbackSpeed: number;
}

// =============================================================================
// API Response Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  pageSize?: number;
  hasMore?: boolean;
}

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// WebSocket Types
// =============================================================================

export type WSEventType = 'initial' | 'position' | 'event' | 'alert' | 'heartbeat';

export interface WSMessage {
  type: WSEventType;
  data?: RTLSPosition | GateEvent | Alert;
  positions?: RTLSPosition[];
  gates?: Gate[];
  alerts?: Alert[];
  timestamp: string;
}
