/**
 * Application Router
 *
 * Defines all routes for the home dashboard hub.
 * Uses ProtectedRoute to guard authenticated routes and handle deep-link redirects.
 */

import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./components/LoginPage";
import DashboardHub from "./components/DashboardHub";
import AccessDenied from "./components/AccessDenied";

export default function App() {
  const auth = useAuth();

  useEffect(() => {
    return auth.events.addUserSignedOut(() => {
      auth.removeUser();
      // No need to redirect if we are already in the "App" router, 
      // the ProtectedRoute or LoginPage will handle the rest, 
      // but explicitly going to login ensures clean state.
      window.location.href = "/login";
    });
  }, [auth]);

  // Show loading while OIDC is initializing
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
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/access-denied" element={<AccessDenied />} />

      {/* Protected routes - require authentication */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardHub />
          </ProtectedRoute>
        }
      />

      {/* Catch-all for unknown routes */}
      <Route
        path="*"
        element={
          <ProtectedRoute>
            <DashboardHub />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
