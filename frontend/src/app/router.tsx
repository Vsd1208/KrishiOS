/**
 * KrishiOS Application Router Configuration.
 *
 * Configures role-protected route trees, nested shells, lazy-loaded dashboard views,
 * and 404 fallback routing using react-router-dom's createBrowserRouter.
 */

import React, { Suspense } from 'react';
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom';
import { LoginPage } from '@/features/auth/LoginPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import { RoleRoute } from '@/features/auth/RoleRoute';
import { FarmerShell } from '@/components/layout/FarmerShell';
import { OfficerShell } from '@/components/layout/OfficerShell';
import { LoadingState } from '@/components/feedback/LoadingState';
import { ErrorState } from '@/components/feedback/ErrorState';
import { RouteError } from '@/components/feedback/RouteError';

// Lazy-loaded farmer views
const FarmerDashboard = React.lazy(() => import('@/pages/farmer/FarmerDashboard'));
const AskPage = React.lazy(() => import('@/pages/farmer/AskPage'));
const FieldsPage = React.lazy(() => import('@/pages/farmer/FieldsPage'));
const AlertsPage = React.lazy(() => import('@/pages/farmer/AlertsPage'));
const ProfilePage = React.lazy(() => import('@/pages/farmer/ProfilePage'));
const GovtUpdatesPage = React.lazy(() => import('@/pages/farmer/GovtUpdatesPage'));
const GrievancePage = React.lazy(() => import('@/pages/farmer/GrievancePage'));
const InsurancePage = React.lazy(() => import('@/pages/farmer/InsurancePage'));

// Lazy-loaded officer views
const OfficerDashboard = React.lazy(() => import('@/pages/officer/OfficerDashboard'));
const ReviewQueuePage = React.lazy(() => import('@/pages/officer/ReviewQueuePage'));
const FarmersDirectoryPage = React.lazy(() => import('@/pages/officer/FarmersDirectoryPage'));
const KnowledgeGraphPage = React.lazy(() => import('@/pages/officer/KnowledgeGraphPage'));
const AnalyticsPage = React.lazy(() => import('@/pages/officer/AnalyticsPage'));
const EvaluationPage = React.lazy(() => import('@/pages/officer/EvaluationPage'));
const FeedbackDashboardPage = React.lazy(() => import('@/pages/officer/FeedbackDashboardPage'));
const ExtensionPage = React.lazy(() => import('@/pages/officer/ExtensionPage'));
const BulletinsPage = React.lazy(() => import('@/pages/officer/BulletinsPage'));
const PublishAdvisoryPage = React.lazy(() => import('@/pages/officer/PublishAdvisoryPage'));
const ConnectAnalyticsPage = React.lazy(() => import('@/pages/officer/ConnectAnalyticsPage'));
const GrievanceQueuePage = React.lazy(() => import('@/pages/officer/GrievanceQueuePage'));
const YieldOutlookPage = React.lazy(() => import('@/pages/officer/YieldOutlookPage'));
const OutbreakMapPage = React.lazy(() => import('@/pages/officer/OutbreakMapPage'));
const DocumentBriefPage = React.lazy(() => import('@/pages/officer/DocumentBriefPage'));

/**
 * Give every route a crash screen. Page routes get one inside the shell (the menu stays usable);
 * top-level routes get a full-page one as the last line of defence, so the app never goes blank.
 */
function withErrorScreens(routes: RouteObject[], depth = 0): RouteObject[] {
  return routes.map((r) => {
    const children = r.children ? withErrorScreens(r.children, depth + 1) : undefined;
    const errorElement = r.errorElement ?? <RouteError fullPage={depth === 0} />;
    return { ...r, errorElement, ...(children ? { children } : {}) } as RouteObject;
  });
}

export const router = createBrowserRouter(withErrorScreens([
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
                    fallback={<LoadingState />}
                  >
                    <FarmerDashboard />
                  </Suspense>
                ),
              },
              {
                path: 'ask',
                element: (
                  <Suspense
                    fallback={<LoadingState />}
                  >
                    <AskPage />
                  </Suspense>
                ),
              },
              {
                path: 'fields',
                element: (
                  <Suspense
                    fallback={<LoadingState />}
                  >
                    <FieldsPage />
                  </Suspense>
                ),
              },
              {
                path: 'alerts',
                element: (
                  <Suspense
                    fallback={<LoadingState />}
                  >
                    <AlertsPage />
                  </Suspense>
                ),
              },
              {
                path: 'updates',
                element: (
                  <Suspense fallback={<LoadingState />}>
                    <GovtUpdatesPage />
                  </Suspense>
                ),
              },
              {
                path: 'help',
                element: (
                  <Suspense fallback={<LoadingState />}>
                    <GrievancePage />
                  </Suspense>
                ),
              },
              {
                path: 'insurance',
                element: (
                  <Suspense fallback={<LoadingState />}>
                    <InsurancePage />
                  </Suspense>
                ),
              },
              {
                path: 'profile',
                element: (
                  <Suspense
                    fallback={<LoadingState />}
                  >
                    <ProfilePage />
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
        element: <RoleRoute allowedRoles={['officer', 'agronomist', 'admin', 'extension_worker']} />,
        children: [
          {
            element: <OfficerShell />,
            children: [
              {
                element: <RoleRoute allowedRoles={['officer', 'agronomist', 'admin']} />,
                children: [
                  {
                    index: true,
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <OfficerDashboard />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'reviews',
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <ReviewQueuePage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'farmers',
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <FarmersDirectoryPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'knowledge',
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <KnowledgeGraphPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'analytics',
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <AnalyticsPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'evaluation',
                    element: (
                      <Suspense
                        fallback={<LoadingState />}
                      >
                        <EvaluationPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'feedback',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <FeedbackDashboardPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'bulletins',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <BulletinsPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'publish',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <PublishAdvisoryPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'connect',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <ConnectAnalyticsPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'grievances',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <GrievanceQueuePage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'yield',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <YieldOutlookPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'outbreaks',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <OutbreakMapPage />
                      </Suspense>
                    ),
                  },
                  {
                    path: 'documents',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <DocumentBriefPage />
                      </Suspense>
                    ),
                  },
                ],
              },
              {
                element: <RoleRoute allowedRoles={['extension_worker', 'officer', 'admin']} />,
                children: [
                  {
                    path: 'extension',
                    element: (
                      <Suspense fallback={<LoadingState />}>
                        <ExtensionPage />
                      </Suspense>
                    ),
                  },
                ],
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
        fullPage
        onRetry={() => {
          window.location.assign('/login');
        }}
      />
    ),
  },
]));

export default router;
