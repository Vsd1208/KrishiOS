/**
 * ProtectedRoute Component.
 *
 * Guards routes that require user authentication.
 * Displays a loading spinner while session state is being verified,
 * redirects unauthenticated users to /login, and renders child routes via <Outlet />.
 */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/Spinner';

export const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center bg-surface p-4"
        role="status"
        aria-live="polite"
      >
        <Spinner size="lg" variant="primary" label="Verifying authentication..." />
        <p className="mt-4 text-small text-text-secondary font-medium">
          Verifying session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Preserve attempted location for post-login redirect
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
