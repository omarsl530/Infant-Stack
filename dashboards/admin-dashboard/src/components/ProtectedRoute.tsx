
import { PropsWithChildren } from 'react';
import { useAuth } from 'react-oidc-context';

interface ProtectedRouteProps extends PropsWithChildren {
  allowedRoles?: string[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-admin-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (auth.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="max-w-md p-6 bg-surface-card rounded-xl border border-red-500/30">
          <h2 className="text-lg font-bold text-red-400 mb-2">Authentication Error</h2>
          <p className="text-slate-400 mb-4">Something went wrong checking your credentials.</p>
          <pre className="text-xs bg-slate-900 p-2 rounded text-red-300 overflow-auto">
            {auth.error.message}
          </pre>
          <button 
            onClick={() => auth.signinRedirect()}
            className="mt-4 px-4 py-2 bg-admin-600 hover:bg-admin-500 text-white rounded-lg w-full"
          >
            Retry Login
          </button>
        </div>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="text-center">
          <div className="w-16 h-16 bg-admin-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-admin-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Admin Dashboard</h1>
          <p className="text-slate-400 mb-8">Please sign in to access the administrative console.</p>
          <button
            onClick={() => auth.signinRedirect()}
            className="px-6 py-3 bg-gradient-to-r from-admin-600 to-admin-500 hover:from-admin-500 hover:to-admin-400 text-white font-medium rounded-lg shadow-lg shadow-admin-500/20 transition-all transform hover:scale-105"
          >
            Sign In with SSO
          </button>
        </div>
      </div>
    );
  }

  // Role check
  if (allowedRoles && allowedRoles.length > 0) {
    // Keycloak typically puts roles in realm_access.roles or resource_access
    const userRoles = (auth.user?.profile as any).realm_access?.roles || [];
    const hasRole = allowedRoles.some(role => userRoles.includes(role));

    if (!hasRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-surface-dark">
          <div className="text-center p-8">
            <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
            <p className="text-slate-400 mb-6">You do not have the required permissions ({allowedRoles.join(', ')}) to view this application.</p>
            <div className="flex gap-4 justify-center">
               <button
                onClick={() => auth.signoutRedirect()}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}
