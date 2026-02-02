/**
 * Protected Route Component for Admin Dashboard
 *
 * Guards routes requiring authentication and admin roles.
 * Redirects unauthenticated users to centralized home-dashboard.
 */

import { PropsWithChildren, useEffect } from "react";
import { useAuth } from "react-oidc-context";

interface ProtectedRouteProps extends PropsWithChildren {
  allowedRoles?: string[];
}

export default function ProtectedRoute({
  children,
  allowedRoles = ["admin"],
}: ProtectedRouteProps) {
  const auth = useAuth();

  // Redirect unauthenticated users to Keycloak SSO
  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      auth.signinRedirect();
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.signinRedirect]);

  if (auth.isLoading || !auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-admin-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400">
            {auth.isLoading ? "Authenticating..." : "Redirecting to login..."}
          </p>
        </div>
      </div>
    );
  }

  if (auth.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="max-w-md p-6 bg-surface-card rounded-xl border border-red-500/30">
          <h2 className="text-lg font-bold text-red-400 mb-2">
            Authentication Error
          </h2>
          <p className="text-slate-400 mb-4">
            Something went wrong checking your credentials.
          </p>
          <pre className="text-xs bg-slate-900 p-2 rounded text-red-300 overflow-auto">
            {auth.error.message}
          </pre>
          <a
            href={HOME_DASHBOARD_URL}
            className="mt-4 block text-center px-4 py-2 bg-admin-600 hover:bg-admin-500 text-white rounded-lg"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  // Role check
  if (allowedRoles && allowedRoles.length > 0) {
    const userRoles = (auth.user?.profile as any).realm_access?.roles || [];
    const hasRole = allowedRoles.some((role) => userRoles.includes(role));

    if (!hasRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-surface-dark">
          <div className="text-center p-8">
            <div className="text-5xl mb-4">🚫</div>
            <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
            <p className="text-slate-400 mb-6">
              You do not have the required permissions ({allowedRoles.join(", ")}) to view this application.
            </p>
            <div className="flex gap-4 justify-center">
              <a
                href={HOME_DASHBOARD_URL}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
              >
                Go to Dashboard Hub
              </a>
              <button
                onClick={() => auth.signoutRedirect()}
                className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}
