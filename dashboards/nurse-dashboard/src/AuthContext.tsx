/**
 * Authentication Context Provider
 *
 * Provides authentication state and methods throughout the React app.
 * Uses Keycloak for OIDC authentication with Authorization Code + PKCE flow.
 */

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import keycloak from './keycloak';

// =============================================================================
// Types
// =============================================================================

interface AuthContextType {
  /** Whether the user is currently authenticated */
  isAuthenticated: boolean;
  /** Whether authentication is still initializing */
  isLoading: boolean;
  /** Current user information */
  user: User | null;
  /** User's roles from Keycloak */
  roles: string[];
  /** Error message if authentication failed */
  error: string | null;
  /** Initiate login redirect to Keycloak */
  login: () => Promise<void>;
  /** Logout and end session */
  logout: () => Promise<void>;
  /** Get current access token (refreshes if needed) */
  getAccessToken: () => Promise<string | null>;
  /** Check if user has a specific role */
  hasRole: (role: string) => boolean;
  /** Check if user has any of the specified roles */
  hasAnyRole: (roles: string[]) => boolean;
  /** Check if user is admin */
  isAdmin: () => boolean;
}

interface User {
  id: string;
  email: string | null;
  username: string | null;
  firstName: string | null;
  lastName: string | null;
  fullName: string;
}

interface AuthProviderProps {
  children: ReactNode;
}

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Token refresh interval (in milliseconds) - refresh when token has < 70 seconds left
const TOKEN_MIN_VALIDITY_SECONDS = 70;
const TOKEN_REFRESH_INTERVAL_MS = 30000; // Check every 30 seconds

// Flag to prevent double initialization in React StrictMode
let keycloakInitialized = false;

// =============================================================================
// Provider Component
// =============================================================================

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  /**
   * Extract roles from Keycloak token.
   * Checks both realm_access and resource_access for roles.
   */
  const extractRoles = useCallback((): string[] => {
    const realmRoles = keycloak.tokenParsed?.realm_access?.roles || [];
    const clientRoles = keycloak.tokenParsed?.resource_access?.[keycloak.clientId || '']?.roles || [];
    
    // Filter out Keycloak internal roles
    const internalRoles = ['offline_access', 'uma_authorization', 'default-roles-infant-stack'];
    return [...new Set([...realmRoles, ...clientRoles])].filter(
      (role) => !internalRoles.includes(role)
    );
  }, []);

  /**
   * Extract user info from Keycloak token.
   */
  const extractUser = useCallback((): User | null => {
    if (!keycloak.tokenParsed) return null;

    const token = keycloak.tokenParsed;
    const firstName = token.given_name || '';
    const lastName = token.family_name || '';
    
    return {
      id: token.sub || '',
      email: token.email || null,
      username: token.preferred_username || null,
      firstName: firstName || null,
      lastName: lastName || null,
      fullName: [firstName, lastName].filter(Boolean).join(' ') || token.preferred_username || 'User',
    };
  }, []);

  /**
   * Update authentication state from Keycloak.
   */
  const updateAuthState = useCallback(() => {
    setIsAuthenticated(keycloak.authenticated || false);
    setUser(keycloak.authenticated ? extractUser() : null);
    setRoles(keycloak.authenticated ? extractRoles() : []);
  }, [extractUser, extractRoles]);

  /**
   * Initialize Keycloak and handle the OIDC flow.
   */
  useEffect(() => {
    // Prevent double initialization in React StrictMode
    if (keycloakInitialized) {
      console.log('[Auth] Keycloak already initialized, skipping...');
      // If already initialized, just update state
      updateAuthState();
      setIsLoading(false);
      return;
    }

    const initKeycloak = async () => {
      try {
        keycloakInitialized = true; // Mark as initialized before calling init
        
        // Initialize with check-sso to silently check for existing session
        const authenticated = await keycloak.init({
          onLoad: 'check-sso',
          pkceMethod: 'S256',
          checkLoginIframe: false, // Disable for better UX
          silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
        });

        console.log('[Auth] Keycloak initialized, authenticated:', authenticated);
        updateAuthState();
        setIsLoading(false);

        // Set up token refresh handler
        keycloak.onTokenExpired = async () => {
          console.log('[Auth] Token expired, refreshing...');
          try {
            const refreshed = await keycloak.updateToken(TOKEN_MIN_VALIDITY_SECONDS);
            if (refreshed) {
              console.log('[Auth] Token refreshed successfully');
              updateAuthState();
            }
          } catch (err) {
            console.error('[Auth] Failed to refresh token:', err);
            setError('Session expired. Please login again.');
            setIsAuthenticated(false);
            setUser(null);
            setRoles([]);
          }
        };

        // Set up auth state change handlers
        keycloak.onAuthSuccess = () => {
          console.log('[Auth] Authentication successful');
          updateAuthState();
        };

        keycloak.onAuthLogout = () => {
          console.log('[Auth] User logged out');
          setIsAuthenticated(false);
          setUser(null);
          setRoles([]);
        };

      } catch (err) {
        console.error('[Auth] Keycloak initialization failed:', err);
        setError('Failed to initialize authentication');
        setIsLoading(false);
      }
    };

    initKeycloak();
  }, [updateAuthState]);

  /**
   * Periodically check and refresh token.
   */
  useEffect(() => {
    if (!isAuthenticated) return;

    const refreshInterval = setInterval(async () => {
      try {
        const refreshed = await keycloak.updateToken(TOKEN_MIN_VALIDITY_SECONDS);
        if (refreshed) {
          console.log('[Auth] Token proactively refreshed');
          updateAuthState();
        }
      } catch (err) {
        console.warn('[Auth] Token refresh failed:', err);
      }
    }, TOKEN_REFRESH_INTERVAL_MS);

    return () => clearInterval(refreshInterval);
  }, [isAuthenticated, updateAuthState]);

  /**
   * Initiate login redirect to Keycloak.
   */
  const login = useCallback(async () => {
    try {
      await keycloak.login({
        redirectUri: window.location.origin,
      });
    } catch (err) {
      console.error('[Auth] Login failed:', err);
      setError('Login failed. Please try again.');
    }
  }, []);

  /**
   * Logout and end Keycloak session.
   */
  const logout = useCallback(async () => {
    try {
      await keycloak.logout({
        redirectUri: window.location.origin,
      });
    } catch (err) {
      console.error('[Auth] Logout failed:', err);
    }
  }, []);

  /**
   * Get current access token, refreshing if necessary.
   */
  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (!keycloak.authenticated) {
      return null;
    }

    try {
      // Refresh if token expires within 30 seconds
      await keycloak.updateToken(30);
      return keycloak.token || null;
    } catch (err) {
      console.error('[Auth] Failed to get access token:', err);
      return null;
    }
  }, []);

  /**
   * Check if user has a specific role.
   */
  const hasRole = useCallback((role: string): boolean => {
    return roles.includes(role);
  }, [roles]);

  /**
   * Check if user has any of the specified roles.
   */
  const hasAnyRole = useCallback((checkRoles: string[]): boolean => {
    return checkRoles.some((role) => roles.includes(role));
  }, [roles]);

  /**
   * Check if user is admin.
   */
  const isAdmin = useCallback((): boolean => {
    return hasRole('admin');
  }, [hasRole]);

  // Context value
  const contextValue: AuthContextType = {
    isAuthenticated,
    isLoading,
    user,
    roles,
    error,
    login,
    logout,
    getAccessToken,
    hasRole,
    hasAnyRole,
    isAdmin,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access authentication context.
 * Must be used within an AuthProvider.
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
