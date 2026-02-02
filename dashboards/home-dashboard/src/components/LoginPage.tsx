/**
 * Login Page Component
 *
 * Centralized login page for all Infant-Stack dashboards.
 * Redirects to Keycloak for OIDC authentication.
 */

import { useAuth } from "react-oidc-context";
import { Navigate } from "react-router-dom";
import { ShieldCheckIcon } from "@heroicons/react/24/outline";

export default function LoginPage() {
  const auth = useAuth();

  // Already authenticated - redirect to dashboard hub
  if (auth.isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  // Loading state
  if (auth.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <div className="spinner" />
          <p className="text-slate-400">Initializing authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900/20 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo and Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 mb-6 shadow-2xl shadow-blue-500/30">
            <ShieldCheckIcon className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">Infant-Stack</h1>
          <p className="text-slate-400 text-lg">
            Hospital Infant Security System
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-card p-8">
          <h2 className="text-xl font-semibold text-white text-center mb-6">
            Welcome Back
          </h2>

          {/* Error display */}
          {auth.error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6">
              <p className="text-red-400 text-sm text-center">
                {auth.error.message || "Authentication failed. Please try again."}
              </p>
            </div>
          )}

          <p className="text-slate-400 text-center mb-8">
            Sign in to access your dashboard. Role-based access will determine
            which dashboards you can view.
          </p>

          {/* Login Button */}
          <button
            onClick={() => auth.signinRedirect()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
              />
            </svg>
            Sign In with SSO
          </button>

          {/* Info */}
          <p className="text-slate-500 text-xs text-center mt-6">
            You will be redirected to the secure Keycloak login portal.
          </p>
        </div>

        {/* Footer */}
        <p className="text-slate-500 text-xs text-center mt-8">
          &copy; 2024 Infant-Stack. Secure infant tracking for hospitals.
        </p>
      </div>
    </div>
  );
}
