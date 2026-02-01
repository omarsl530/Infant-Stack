/**
 * API client for Admin Dashboard
 */

import { User, UserListResponse, UserCreateRequest, UserUpdateRequest, AuditLogListResponse } from './types';

const API_BASE = '/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }
  
  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

// =============================================================================
// User API
// =============================================================================

export async function fetchUsers(params?: {
  page?: number;
  limit?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
}): Promise<UserListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', params.page.toString());
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.role) query.set('role', params.role);
  if (params?.is_active !== undefined) query.set('is_active', params.is_active.toString());
  if (params?.search) query.set('search', params.search);
  
  const response = await fetch(`${API_BASE}/users?${query}`);
  return handleResponse<UserListResponse>(response);
}

export async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`${API_BASE}/users/${id}`);
  return handleResponse<User>(response);
}

export async function createUser(data: UserCreateRequest): Promise<User> {
  const response = await fetch(`${API_BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<User>(response);
}

export async function updateUser(id: string, data: UserUpdateRequest): Promise<User> {
  const response = await fetch(`${API_BASE}/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<User>(response);
}

export async function deleteUser(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/users/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<void>(response);
}

export async function assignRole(userId: string, role: string): Promise<User> {
  const response = await fetch(`${API_BASE}/users/${userId}/role`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  return handleResponse<User>(response);
}

export async function resetUserPassword(userId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/users/${userId}/reset-password`, {
    method: 'POST',
  });
  return handleResponse<void>(response);
}

// =============================================================================
// Audit Logs API
// =============================================================================

export async function fetchAuditLogs(params?: {
  page?: number;
  limit?: number;
  user_id?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  from?: string;
  to?: string;
}): Promise<AuditLogListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', params.page.toString());
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.user_id) query.set('user_id', params.user_id);
  if (params?.action) query.set('action', params.action);
  if (params?.resource_type) query.set('resource_type', params.resource_type);
  if (params?.resource_id) query.set('resource_id', params.resource_id);
  if (params?.from) query.set('from_time', params.from);
  if (params?.to) query.set('to_time', params.to);
  
  const response = await fetch(`${API_BASE}/audit-logs?${query}`);
  return handleResponse<AuditLogListResponse>(response);
}

export async function fetchAuditFilters(): Promise<{ actions: string[], resource_types: string[] }> {
  const response = await fetch(`${API_BASE}/audit-logs/filters`);
  return handleResponse<{ actions: string[], resource_types: string[] }>(response);
}

// =============================================================================
// Current User API
// =============================================================================

export async function fetchCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE}/users/me`);
  return handleResponse<User>(response);
}

export async function updateCurrentUser(data: UserUpdateRequest): Promise<User> {
  const response = await fetch(`${API_BASE}/users/me`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<User>(response);
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await fetch(`${API_BASE}/users/me/password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  return handleResponse<void>(response);
}

export { ApiError };
