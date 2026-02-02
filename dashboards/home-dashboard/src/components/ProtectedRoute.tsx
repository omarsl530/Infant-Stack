/**
 * Protected Route Component
 *
 * Guards routes that require authentication and optionally specific roles.
 * Handles deep-link redirect: stores attempted URL for post-login navigation.
 *
 * Security:
 * - Client-side check for UX (showing appropriate UI)
 * - Server-side MUST also validate on API calls (source of truth)
 */

import { ReactNode, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "react-oidc-context";

interface ProtectedRouteProps {
  children: ReactNode;
  /** Required roles to access this route (any of them grants access) */
  requiredRoles?: string[];
  /** If true, user must have ALL required roles */
  requireAllRoles?: boolean;
}

// Session storage key for deep-link redirect
const REDIRECT_KEY = "infant_stack_redirect_url";

/**
 * Extracts user roles from Keycloak token.
 * Checks realm_access.roles in the OIDC profile.
 */
function extractRoles(profile: any): string[] {
  const realmRoles = profile?.realm_access?.roles || [];
  // Filter out Keycloak internal roles
  const internalRoles = [
    "offline_access",
    "uma_authorization",
    "default-roles-infant-stack",
  ];
  return realmRoles.filter((role: string) => !internalRoles.includes(role));
}

export default function ProtectedRoute({
  children,
  requiredRoles,
  requireAllRoles = false,
}: ProtectedRouteProps) {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Store attempted URL for post-login redirect
  useEffect(() => {
    if (!auth.isAuthenticated && !auth.isLoading) {
      // Save the current path for redirect after login
      const attemptedUrl = location.pathname + location.search;
      if (attemptedUrl !== "/" && attemptedUrl !== "/login") {
        sessionStorage.setItem(REDIRECT_KEY, attemptedUrl);
      }
    }
  }, [auth.isAuthenticated, auth.isLoading, location]);

  // Loading state
  if (auth.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <div className="spinner" />
          <p className="text-slate-400">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Authentication error
  if (auth.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="glass-card max-w-md p-8 text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Authentication Error
          </h1>
          <p className="text-slate-400 mb-4">
            Something went wrong during authentication.
          </p>
          <pre className="text-xs bg-slate-900 p-3 rounded-lg text-red-300 overflow-auto mb-4">
            {auth.error.message}
          </pre>
          <button onClick={() => auth.signinRedirect()} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Not authenticated - redirect to login
  if (!auth.isAuthenticated) {
    // Trigger Keycloak login redirect
    auth.signinRedirect();

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <div className="spinner" />
          <p className="text-slate-400">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Check role requirements
  if (requiredRoles && requiredRoles.length > 0) {
    const userRoles = extractRoles(auth.user?.profile);

    const hasAccess = requireAllRoles
      ? requiredRoles.every((role) => userRoles.includes(role))
      : requiredRoles.some((role) => userRoles.includes(role));

    if (!hasAccess) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
          <div className="glass-card max-w-md p-8 text-center">
            <div className="text-6xl mb-4">🚫</div>
            <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
            <p className="text-slate-400 mb-4">
              You don't have permission to access this page.
            </p>
            <p className="text-slate-500 text-sm mb-6">
              Required roles: {requiredRoles.join(", ")}
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => navigate("/")}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Go to Dashboard
              </button>
              <button
                onClick={() => auth.signoutRedirect()}
                className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      );
    }
  }

  // Check for deep-link redirect after successful authentication
  useEffect(() => {
    if (auth.isAuthenticated) {
      const redirectUrl = sessionStorage.getItem(REDIRECT_KEY);
      if (redirectUrl) {
        sessionStorage.removeItem(REDIRECT_KEY);
        // Only redirect if not already on the target path
        if (location.pathname !== redirectUrl.split("?")[0]) {
          navigate(redirectUrl, { replace: true });
        }
      }
    }
  }, [auth.isAuthenticated, navigate, location.pathname]);

  // Authenticated and authorized - render children
  return <>{children}</>;
}

export { REDIRECT_KEY, extractRoles };
