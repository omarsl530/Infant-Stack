/**
 * Main Application Entry Point
 *
 * Sets up React with OIDC authentication provider and routing.
 * This is the centralized authentication hub for all Infant-Stack dashboards.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider, AuthProviderProps } from "react-oidc-context";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

/**
 * OIDC Configuration for Keycloak
 *
 * Uses Authorization Code flow with PKCE (Proof Key for Code Exchange)
 * for secure public client authentication.
 */
const oidcConfig: AuthProviderProps = {
  authority:
    import.meta.env.VITE_KEYCLOAK_URL ||
    "http://localhost:8080/realms/infant-stack",
  client_id: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "infant-stack-spa",
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: "http://localhost:3003/login",
  scope: "openid profile email roles",

  // Clean up URL after successful login (remove code/state params)
  onSigninCallback: () => {
    window.history.replaceState({}, document.title, window.location.pathname);
  },
  monitorSession: true, // Enable global logout detection

  // Automatic silent token refresh
  automaticSilentRenew: true,

  // Load user info from Keycloak userinfo endpoint
  loadUserInfo: true,
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider {...oidcConfig}>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
