/**
 * Protected Route Component for Security Dashboard
 *
 * Guards routes that require authentication and the 'security' role.
 * Redirects unauthenticated users to centralized home-dashboard.
 */

import { ReactNode, useEffect } from "react";
import { useAuth } from "react-oidc-context";

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: string[];
}

/**
 * Extracts user roles from Keycloak token profile
 */
function extractRoles(profile: any): string[] {
  const realmRoles = profile?.realm_access?.roles || [];
  const internalRoles = [
    "offline_access",
    "uma_authorization",
    "default-roles-infant-stack",
  ];
  return realmRoles.filter((role: string) => !internalRoles.includes(role));
}

export default function ProtectedRoute({
  children,
  allowedRoles = ["security", "admin"],
}: ProtectedRouteProps) {
  const auth = useAuth();

  // Redirect unauthenticated users to Keycloak SSO
  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      auth.signinRedirect();
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.signinRedirect]);

  // Loading state
  if (auth.isLoading || !auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400">
            {auth.isLoading ? "Checking authentication..." : "Redirecting to login..."}
          </p>
        </div>
      </div>
    );
  }

  // Auth error
  if (auth.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="max-w-md p-8 bg-slate-800 rounded-2xl text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h1 className="text-xl font-bold text-white mb-2">
            Authentication Error
          </h1>
          <p className="text-slate-400 mb-4">{auth.error.message}</p>
          <a
            href={HOME_DASHBOARD_URL}
            className="inline-block px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  // Check roles
  const userRoles = extractRoles(auth.user?.profile);
  const hasRole = allowedRoles.some((role) => userRoles.includes(role));

  if (!hasRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
        <div className="max-w-md p-8 bg-slate-800 rounded-2xl text-center">
          <div className="text-5xl mb-4">🚫</div>
          <h1 className="text-xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-slate-400 mb-4">
            You need one of these roles: {allowedRoles.join(", ")}
          </p>
          <p className="text-slate-500 text-sm mb-6">
            Your roles: {userRoles.join(", ") || "none"}
          </p>
          <div className="flex gap-3 justify-center">
            <a
              href={HOME_DASHBOARD_URL}
              className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl"
            >
              Go Home
            </a>
            <button
              onClick={() => auth.signoutRedirect()}
              className="px-6 py-3 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-xl"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Authorized
  return <>{children}</>;
}

