/**
 * Dashboard Hub Component
 *
 * Central navigation hub showing all available dashboards.
 * Links are shown/hidden based on user roles (client-side UX only).
 * Server-side enforces actual access control.
 */

import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import {
  ShieldCheckIcon,
  UserGroupIcon,
  BeakerIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  MapIcon,
  HeartIcon,
} from "@heroicons/react/24/outline";
import { extractRoles } from "./ProtectedRoute";

/**
 * Dashboard configuration with role requirements.
 * Each dashboard has a URL, required roles, and display info.
 */
interface DashboardConfig {
  id: string;
  name: string;
  description: string;
  url: string;
  port: number;
  requiredRoles: string[];
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}

const DASHBOARDS: DashboardConfig[] = [
  {
    id: "nurse",
    name: "Nurse Dashboard",
    description: "Manage infants, mothers, and tag assignments",
    url: "http://localhost:3000",
    port: 3000,
    requiredRoles: ["nurse", "admin"],
    icon: HeartIcon,
    color: "text-pink-400",
    bgColor: "bg-pink-500/20",
  },
  {
    id: "security",
    name: "Security Dashboard",
    description: "Real-time tracking, alerts, gates, and cameras",
    url: "http://localhost:3001",
    port: 3001,
    requiredRoles: ["security", "admin"],
    icon: MapIcon,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/20",
  },
  {
    id: "admin",
    name: "Admin Dashboard",
    description: "User management, roles, audit logs, and configuration",
    url: "http://localhost:3002",
    port: 3002,
    requiredRoles: ["admin"],
    icon: Cog6ToothIcon,
    color: "text-amber-400",
    bgColor: "bg-amber-500/20",
  },

];

export default function DashboardHub() {
  const auth = useAuth();
  const user = auth.user?.profile;
  const userRoles = extractRoles(user);

  // Handle returnUrl redirect after login
  useEffect(() => {
    if (auth.isAuthenticated) {
      const params = new URLSearchParams(window.location.search);
      const returnUrl = params.get("returnUrl");
      if (returnUrl) {
        // Clear the returnUrl from address bar and redirect
        window.history.replaceState({}, document.title, window.location.pathname);
        window.location.href = decodeURIComponent(returnUrl);
      }
    }
  }, [auth.isAuthenticated]);

  // Check if user has access to a dashboard
  const hasAccess = (dashboard: DashboardConfig): boolean => {
    return dashboard.requiredRoles.some((role) => userRoles.includes(role));
  };

  // Get accessible dashboards
  const accessibleDashboards = DASHBOARDS.filter(hasAccess);
  const inaccessibleDashboards = DASHBOARDS.filter((d) => !hasAccess(d));

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-lg border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <ShieldCheckIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold gradient-text">Infant-Stack</h1>
                <p className="text-xs text-slate-400">Dashboard Hub</p>
              </div>
            </div>

            <div className="flex items-center gap-6">
              {/* User Info */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold">
                  {(user?.given_name?.[0] || "U").toUpperCase()}
                  {(user?.family_name?.[0] || "").toUpperCase()}
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">
                    {user?.given_name} {user?.family_name}
                  </p>
                  <p className="text-xs text-slate-400">{user?.email}</p>
                </div>
              </div>

              {/* Role badges */}
              <div className="hidden md:flex items-center gap-2">
                {userRoles.map((role) => (
                  <span
                    key={role}
                    className="px-2 py-1 text-xs font-medium rounded-full bg-primary-500/20 text-primary-400 border border-primary-500/30"
                  >
                    {role}
                  </span>
                ))}
              </div>

              {/* Logout */}
              <button
                onClick={() => auth.signoutRedirect()}
                className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                title="Sign Out"
              >
                <ArrowRightOnRectangleIcon className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Welcome Section */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-4">
            Welcome, {user?.given_name || "User"}!
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Select a dashboard below to get started. You have access to{" "}
            <span className="text-primary-400 font-semibold">
              {accessibleDashboards.length} dashboard
              {accessibleDashboards.length !== 1 ? "s" : ""}
            </span>{" "}
            based on your roles.
          </p>
        </div>

        {/* Accessible Dashboards Grid */}
        {accessibleDashboards.length > 0 && (
          <section className="mb-12">
            <h3 className="text-xl font-semibold text-white mb-6">
              Your Dashboards
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {accessibleDashboards.map((dashboard) => (
                <DashboardCard
                  key={dashboard.id}
                  dashboard={dashboard}
                  hasAccess={true}
                />
              ))}
            </div>
          </section>
        )}

        {accessibleDashboards.length === 0 && (
          <div className="text-center py-12 bg-slate-800/50 rounded-2xl border border-slate-700/50">
            <ShieldCheckIcon className="w-16 h-16 text-slate-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Access Restricted</h3>
            <p className="text-slate-400 max-w-md mx-auto">
              Your account (`{userRoles.join(", ")}`) does not have access to any specific dashboards yet.
              <br className="mb-2"/>
              Please contact an administrator to assign the necessary roles.
            </p>
          </div>
        )}

        {/* Inaccessible Dashboards are now hidden per security requirements */}
      </main>
    </div>
  );
}

/**
 * Individual dashboard card component
 */
function DashboardCard({
  dashboard,
  hasAccess,
}: {
  dashboard: DashboardConfig;
  hasAccess: boolean;
}) {
  const Icon = dashboard.icon;

  const handleClick = () => {
    if (hasAccess) {
      // Open dashboard in new tab (or same tab if preferred)
      window.location.href = dashboard.url;
    }
  };

  return (
    <div
      onClick={handleClick}
      data-disabled={!hasAccess}
      className={`dashboard-card ${!hasAccess ? "opacity-50 cursor-not-allowed" : ""}`}
      role="button"
      tabIndex={hasAccess ? 0 : -1}
      onKeyPress={(e) => e.key === "Enter" && handleClick()}
    >
      <div className="flex items-start gap-4">
        <div
          className={`p-3 rounded-xl ${dashboard.bgColor} ${dashboard.color}`}
        >
          <Icon className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-white mb-1">{dashboard.name}</h4>
          <p className="text-sm text-slate-400 mb-3">{dashboard.description}</p>
          <div className="flex flex-wrap gap-1">
            {dashboard.requiredRoles.map((role) => (
              <span
                key={role}
                className="px-2 py-0.5 text-xs rounded bg-slate-700/50 text-slate-400"
              >
                {role}
              </span>
            ))}
          </div>
        </div>
      </div>
      {hasAccess && (
        <div className="mt-4 pt-4 border-t border-slate-700/50 text-right">
          <span className="text-sm text-primary-400 font-medium">
            Open Dashboard →
          </span>
        </div>
      )}
      {!hasAccess && (
        <div className="mt-4 pt-4 border-t border-slate-700/50 text-center">
          <span className="text-xs text-slate-500">
            Contact admin for access
          </span>
        </div>
      )}
    </div>
  );
}
