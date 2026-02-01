/**
 * Login Page Component
 *
 * Displays login button and handles redirect to Keycloak.
 * Shows loading state during authentication initialization.
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';
import { useAuth } from './AuthContext';

export default function LoginPage() {
  const { isAuthenticated, isLoading, error, login } = useAuth();

  // Redirect to dashboard if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-300 text-lg">Initializing authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-blue-500/20 mb-4">
            <ShieldCheckIcon className="w-10 h-10 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Infant-Stack</h1>
          <p className="text-gray-400">Hospital Infant Security Dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/10">
          <h2 className="text-xl font-semibold text-white text-center mb-6">
            Welcome Back
          </h2>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-6">
              <p className="text-red-400 text-sm text-center">{error}</p>
            </div>
          )}

          <p className="text-gray-400 text-center mb-6">
            Sign in to access the nurse dashboard and manage infant tracking.
          </p>

          {/* Login Button */}
          <button
            onClick={() => login()}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 transform hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900"
          >
            Sign In with Keycloak
          </button>

          {/* Info Text */}
          <p className="text-gray-500 text-xs text-center mt-6">
            You will be redirected to the secure login portal.
          </p>
        </div>

        {/* Footer */}
        <p className="text-gray-500 text-xs text-center mt-8">
          &copy; 2024 Infant-Stack. Secure infant tracking for hospitals.
        </p>
      </div>
    </div>
  );
}
