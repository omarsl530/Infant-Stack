/**
 * Access Denied Page
 *
 * Shown when a user is authenticated but lacks required roles.
 * Provides navigation back to the dashboard hub.
 */

import { Link } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { ShieldExclamationIcon } from "@heroicons/react/24/outline";

export default function AccessDenied() {
  const auth = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-red-900/10 to-slate-900 flex items-center justify-center p-4">
      <div className="glass-card max-w-md p-8 text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-red-500/20 mb-6">
          <ShieldExclamationIcon className="w-10 h-10 text-red-400" />
        </div>

        <h1 className="text-3xl font-bold text-white mb-2">Access Denied</h1>

        <p className="text-slate-400 mb-6">
          You don't have the required permissions to access this page. Please
          contact your administrator if you believe this is an error.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/"
            className="px-6 py-3 bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-xl transition-colors"
          >
            Go to Dashboard Hub
          </Link>

          <button
            onClick={() => auth.signoutRedirect()}
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-xl transition-colors"
          >
            Sign Out
          </button>
        </div>

        <p className="text-slate-500 text-xs mt-8">
          Error Code: 403 Forbidden
        </p>
      </div>
    </div>
  );
}
