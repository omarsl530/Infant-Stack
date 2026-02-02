/**
 * Protected Route Component
 *
 * Wrapper for routes that require authentication.
 * Redirects unauthenticated users to the centralized home-dashboard for login.
 */

import { ReactNode, useEffect } from "react";

import { useAuth } from "./AuthContext";

const HOME_DASHBOARD_URL = "http://localhost:3003";

interface ProtectedRouteProps {
  children: ReactNode;
  /** Optional: Required roles to access this route */
  requiredRoles?: string[];
  /** If true, user must have ALL required roles. If false, ANY role suffices. */
  requireAll?: boolean;
}

export default function ProtectedRoute({
  children,
  requiredRoles,
  requireAll = false,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, roles, login } = useAuth();


  // Redirect to Keycloak SSO if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      login();
    }
  }, [isLoading, isAuthenticated, login]);

  // Show loading state while auth is initializing or redirecting
  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-300">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Check role requirements if specified
  if (requiredRoles && requiredRoles.length > 0) {
    const hasAccess = requireAll
      ? requiredRoles.every((role) => roles.includes(role))
      : requiredRoles.some((role) => roles.includes(role));

    if (!hasAccess) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/10 max-w-md text-center">
            <div className="text-red-400 text-6xl mb-4">🚫</div>
            <h1 className="text-2xl font-bold text-white mb-2">
              Access Denied
            </h1>
            <p className="text-gray-400 mb-6">
              You don't have permission to access this page.
            </p>
            <p className="text-gray-500 text-sm mb-4">
              Required roles: {requiredRoles.join(", ")}
            </p>
            <a
              href={HOME_DASHBOARD_URL}
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
            >
              Go to Dashboard Hub
            </a>
          </div>
        </div>
      );
    }
  }

  // Render the protected content
  return <>{children}</>;
}

