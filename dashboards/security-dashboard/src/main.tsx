/**
 * Security Dashboard Entry Point
 *
 * Wraps the application with OIDC authentication provider.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider, AuthProviderProps } from "react-oidc-context";
import App from "./App";
import ProtectedRoute from "./components/ProtectedRoute";
import "./index.css";

/**
 * OIDC Configuration for Keycloak
 */
const oidcConfig: AuthProviderProps = {
  authority:
    import.meta.env.VITE_KEYCLOAK_URL ||
    "http://localhost:8080/realms/infant-stack",
  client_id: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "infant-stack-spa",
  // Redirect to Home Dashboard after login (must be handled via callback to avoid state mismatch)
  redirect_uri: window.location.origin,
  // Redirect to Home Dashboard login after logout
  post_logout_redirect_uri: "http://localhost:3003/login",
  response_type: "code",
  scope: "openid profile email roles",

  onSigninCallback: () => {
    window.history.replaceState({}, document.title, window.location.pathname);
  },

  automaticSilentRenew: true,
  loadUserInfo: true,
  monitorSession: true, // Enable listening for session changes
};

import { ErrorBoundary } from "./components/ErrorBoundary";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider {...oidcConfig}>
        <ProtectedRoute allowedRoles={["security", "admin"]}>
          <App />
        </ProtectedRoute>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

