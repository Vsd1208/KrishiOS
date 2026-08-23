/**
 * KrishiOS Application Router Configuration.
 *
 * Configures role-protected route trees, nested shells, lazy-loaded dashboard views,
 * and 404 fallback routing using react-router-dom's createBrowserRouter.
 */

import React, { Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginPage } from '@/features/auth/LoginPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import { RoleRoute } from '@/features/auth/RoleRoute';
import { FarmerShell } from '@/components/layout/FarmerShell';
import { OfficerShell } from '@/components/layout/OfficerShell';
import { LoadingState } from '@/components/feedback/LoadingState';
import { ErrorState } from '@/components/feedback/ErrorState';

// Lazy-loaded page components for bundle optimization
const FarmerDashboard = React.lazy(() => import('@/pages/farmer/FarmerDashboard'));
const OfficerDashboard = React.lazy(() => import('@/pages/officer/OfficerDashboard'));

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <Navigate to="/login" replace />,
  },
  {
    path: '/farmer',
    element: <ProtectedRoute />,
    children: [
      {
        element: <RoleRoute allowedRoles={['farmer']} />,
        children: [
          {
            element: <FarmerShell />,
            children: [
              {
                index: true,
                element: (
                  <Suspense
                    fallback={<LoadingState fullPage message="Loading Farmer Dashboard..." />}
                  >
                    <FarmerDashboard />
                  </Suspense>
                ),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '/officer',
    element: <ProtectedRoute />,
    children: [
      {
        element: <RoleRoute allowedRoles={['officer', 'agronomist', 'admin']} />,
        children: [
          {
            element: <OfficerShell />,
            children: [
              {
                index: true,
                element: (
                  <Suspense
                    fallback={<LoadingState fullPage message="Loading Officer Dashboard..." />}
                  >
                    <OfficerDashboard />
                  </Suspense>
                ),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: (
      <ErrorState
        statusCode={404}
        title="404 — Page Not Found"
        message="The page or view you requested does not exist or has been moved."
        fullPage
        onRetry={() => {
          window.location.assign('/login');
        }}
      />
    ),
  },
]);

export default router;
