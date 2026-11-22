/**
 * RoleRoute Component.
 *
 * Role-Based Access Control (RBAC) guard for routes.
 * Compares current user's role against `allowedRoles`.
 * If allowed, renders child routes via <Outlet />.
 * If forbidden, renders an accessible 403 error state.
 */

import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types/auth';
import { ShieldAlert, ArrowLeft, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useTranslation } from 'react-i18next';

export interface RoleRouteProps {
  allowedRoles: UserRole[];
}

export const RoleRoute: React.FC<RoleRouteProps> = ({ allowedRoles }) => {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center bg-surface p-4"
        role="status"
        aria-live="polite"
      >
        <Spinner size="lg" variant="primary" label={t('shell.checkingAccess')} />
        <p className="mt-4 text-small text-text-secondary font-medium">{t('shell.checkingAccess')}</p>
      </div>
    );
  }

  const isRoleAllowed = user && allowedRoles.includes(user.role);

  if (!isRoleAllowed) {
    return (
      <main
        className="min-h-screen flex items-center justify-center bg-surface-raised p-4 sm:p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="max-w-md w-full bg-surface border border-border rounded-xl p-6 sm:p-8 text-center shadow-card space-y-5">
          <div className="w-14 h-14 rounded-full bg-danger-50 text-danger-600 flex items-center justify-center mx-auto">
            <ShieldAlert className="w-8 h-8" aria-hidden="true" />
          </div>

          <div className="space-y-2">
            <h1 className="text-heading font-semibold text-text">{t('errorState.denied.title')}</h1>
            <p className="text-body text-text-secondary">
              {t('shell.roleDenied', {
                role: user?.role ? t(`roles.${user.role}`, { defaultValue: user.role }) : '—',
              })}
            </p>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              variant="outline"
              size="md"
              leftIcon={<ArrowLeft className="w-4 h-4" aria-hidden="true" />}
              onClick={() => {
                if (user?.role === 'farmer') {
                  navigate('/farmer', { replace: true });
                } else if (user?.role === 'extension_worker') {
                  navigate('/officer/extension', { replace: true });
                } else if (
                  user?.role === 'officer' ||
                  user?.role === 'agronomist' ||
                  user?.role === 'admin'
                ) {
                  navigate('/officer', { replace: true });
                } else {
                  navigate('/login', { replace: true });
                }
              }}
            >
              {t('shell.backHome')}
            </Button>

            <Button
              variant="ghost"
              size="md"
              leftIcon={<LogOut className="w-4 h-4" aria-hidden="true" />}
              onClick={() => logout()}
            >
              {t('auth.logout')}
            </Button>
          </div>
        </div>
      </main>
    );
  }

  return <Outlet />;
};

export default RoleRoute;
