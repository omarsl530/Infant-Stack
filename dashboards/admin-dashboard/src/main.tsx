import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider } from "react-oidc-context";
import App from "./App.tsx";
import "./index.css";

const oidcConfig = {
  authority: "http://localhost:8080/realms/infant-stack",
  client_id: "infant-stack-spa",
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: "http://localhost:3003/login",
  onSigninCallback: () => {
    // Remove the code and state from URL after successful login
    window.history.replaceState({}, document.title, window.location.pathname);
  },
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider {...oidcConfig}>
      <App />
    </AuthProvider>
  </React.StrictMode>,
);
