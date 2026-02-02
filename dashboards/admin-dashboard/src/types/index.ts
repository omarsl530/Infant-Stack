// User types
// Role can be a string now (custom roles)
export type UserRole = string;

export interface Role {
  id: string;
  name: string;
  description: string | null;
  permissions: Record<string, string[]>;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  user_count?: number;
}

export interface RoleCreate {
  name: string;
  description?: string;
  permissions: Record<string, string[]>;
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  permissions?: Record<string, string[]>;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string; // Changed from UserRole enum to string
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  limit: number;
}

export interface UserCreateRequest {
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  password: string;
}

export interface UserUpdateRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_active?: boolean;
}

// Audit log types
export interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  limit: number;
}

// Config types
// Config types
export type ConfigType = "string" | "integer" | "float" | "boolean" | "json";

export interface ConfigResponse {
  key: string;
  value: any;
  type: ConfigType;
  description: string | null;
  is_public: boolean;
  updated_at: string;
  updated_by: string | null;
}

export interface ConfigUpdate {
  value: any;
  description?: string;
}

export interface ConfigCreate extends ConfigUpdate {
  key: string;
  type: ConfigType;
  is_public?: boolean;
}

// Zone types
export interface Zone {
  id: string;
  name: string;
  floor: string;
  zone_type: "AUTHORIZED" | "RESTRICTED" | "EXIT";
  polygon: { x: number; y: number }[];
  color: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ZoneCreate {
  name: string;
  floor: string;
  zone_type: string;
  polygon: { x: number; y: number }[];
  color?: string;
}

export interface ZoneUpdate extends Partial<ZoneCreate> {
  is_active?: boolean;
}

export interface ZoneListResponse {
  items: Zone[];
  total: number;
}

// Floorplan types
export interface Floorplan {
  id: string;
  floor: string;
  name: string;
  image_url: string;
  width: number;
  height: number;
  scale: number;
  origin_x: number;
  origin_y: number;
  created_at: string;
}

export interface FloorplanCreate {
  floor: string;
  name: string;
  image_url: string;
  width: number;
  height: number;
  scale?: number;
  origin_x?: number;
  origin_y?: number;
}

export interface FloorplanListResponse {
  items: Floorplan[];
  total: number;
}

// Navigation types

// Link/Nav types
export interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  path?: string;
}

// Stats types
export interface DashboardStats {
  users: {
    total: number;
    active_sessions: number;
    new_this_month: number;
  };
  tags: {
    total_active: number;
    infants: number;
    mothers: number;
  };
  alerts: {
    today: number;
    unacknowledged: number;
  };
}
