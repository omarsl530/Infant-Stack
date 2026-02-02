/**
 * Main Application Entry Point
 *
 * Sets up React with BrowserRouter and AuthProvider for the dashboard.
 * Login is handled by the centralized home-dashboard at port 3003.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import ProtectedRoute from "./ProtectedRoute";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* All routes are protected - login is at home-dashboard */}
          <Route
            path="/*"
            element={
              <ProtectedRoute requiredRoles={["nurse", "admin"]}>
                <App />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
