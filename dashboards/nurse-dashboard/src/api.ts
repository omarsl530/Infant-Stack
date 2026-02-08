/**
 * API client for communicating with the Infant-Stack backend.
 *
 * All requests include the JWT Bearer token from Keycloak when authenticated.
 */

import keycloak from "./keycloak";

const API_BASE = "/api/v1";

// =============================================================================
// Types
// =============================================================================

export interface InfantAPI {
  id: string;
  tag_id: string;
  name: string;
  ward: string;
  room: string | null;
  tag_status: string;
  date_of_birth: string | null;
  weight?: string;
  mother_name: string | null;
  mother_tag_id: string | null;
  created_at: string;
}

export interface MotherAPI {
  id: string;
  tag_id: string;
  name: string;
  room: string | null;
  contact_number: string | null;
  tag_status: string;
  created_at: string;
}

export interface AlertAPI {
  id: string;
  alert_type: string;
  severity: string;
  message: string;
  tag_id: string | null;
  acknowledged: boolean;
  created_at: string;
}

// =============================================================================
// Authenticated Fetch Helper
// =============================================================================

/**
 * Get headers with authentication token.
 * Refreshes token if needed before returning.
 */
async function getAuthHeaders(): Promise<HeadersInit> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (keycloak.authenticated) {
    try {
      // Refresh token if it expires within 30 seconds
      await keycloak.updateToken(30);
      if (keycloak.token) {
        headers["Authorization"] = `Bearer ${keycloak.token}`;
      }
    } catch (error) {
      console.error("[API] Token refresh failed:", error);
      // Token refresh failed - user may need to re-authenticate
      throw new Error("Session expired. Please login again.");
    }
  }

  return headers;
}

/**
 * Authenticated fetch wrapper.
 * Automatically adds Bearer token to requests.
 */
async function authFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = await getAuthHeaders();

  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers || {}),
    },
  });
}

// =============================================================================
// Response Handler
// =============================================================================

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    // Token is invalid or expired
    throw new Error("Authentication required. Please login.");
  }

  if (response.status === 403) {
    throw new Error(
      "Access denied. You do not have permission for this action.",
    );
  }

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// =============================================================================
// Infants API
// =============================================================================

export async function fetchInfants(): Promise<InfantAPI[]> {
  const response = await authFetch(`${API_BASE}/infants/`);
  const data = await handleResponse<{ items: InfantAPI[]; total: number }>(
    response,
  );
  return data.items;
}

export async function createInfant(infant: {
  tag_id: string;
  name: string;
  ward: string;
  room?: string;
  date_of_birth?: string;
  weight?: string;
}): Promise<InfantAPI> {
  const response = await authFetch(`${API_BASE}/infants/`, {
    method: "POST",
    body: JSON.stringify(infant),
  });
  return handleResponse<InfantAPI>(response);
}

export async function deleteInfant(infantId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/infants/${infantId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    await handleResponse(response);
  }
}

// =============================================================================
// Mothers API
// =============================================================================

export async function fetchMothers(): Promise<MotherAPI[]> {
  const response = await authFetch(`${API_BASE}/mothers/`);
  const data = await handleResponse<{ items: MotherAPI[]; total: number }>(
    response,
  );
  return data.items;
}

export async function createMother(mother: {
  tag_id: string;
  name: string;
  room?: string;
  contact_number?: string;
}): Promise<MotherAPI> {
  const response = await authFetch(`${API_BASE}/mothers/`, {
    method: "POST",
    body: JSON.stringify(mother),
  });
  return handleResponse<MotherAPI>(response);
}

export async function deleteMother(motherId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/mothers/${motherId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    await handleResponse(response);
  }
}

// =============================================================================
// Alerts API
// =============================================================================

export async function fetchAlerts(): Promise<AlertAPI[]> {
  const response = await authFetch(`${API_BASE}/alerts/?acknowledged=false`);
  const data = await handleResponse<{ items: AlertAPI[]; total: number }>(
    response,
  );
  return data.items;
}

export async function dismissAlert(alertId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/alerts/${alertId}`, {
    method: "DELETE",
  });
  await handleResponse<{ status: string }>(response);
}

// =============================================================================
// Pairings API
// =============================================================================

export async function pairInfantToMother(
  infantId: string,
  motherId: string,
): Promise<any> {
  const response = await authFetch(`${API_BASE}/pairings/`, {
    method: "POST",
    body: JSON.stringify({ infant_id: infantId, mother_id: motherId }),
  });
  return handleResponse(response);
}

export async function deletePairing(pairingId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/pairings/${pairingId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    await handleResponse(response);
  }
}
