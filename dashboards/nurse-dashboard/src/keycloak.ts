/**
 * Keycloak Instance Configuration
 *
 * Initializes and exports the Keycloak adapter for OIDC authentication.
 * Uses environment variables for configuration in production.
 */

import Keycloak from "keycloak-js";

// Keycloak configuration - uses environment variables or defaults for development
const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080",
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "infant-stack",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "infant-stack-spa",
};

// Create and export the Keycloak instance
const keycloak = new Keycloak(keycloakConfig);

export default keycloak;
