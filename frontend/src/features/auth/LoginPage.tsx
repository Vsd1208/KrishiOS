/**
 * Login Page Component for KrishiOS.
 *
 * Supports login via mobile phone number or email address with password.
 * Redirects authenticated users to role-specific shells (/farmer or /officer).
 */

import React, { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { ApiError } from '@/types/api';
import type { LoginRequest, UserRole } from '@/types/auth';
import { Sprout, Phone, Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';

/**
 * Returns the destination route for a given user role.
 */
function getRoleRedirectPath(role: UserRole): string {
  switch (role) {
    case 'farmer':
      return '/farmer';
    case 'officer':
    case 'agronomist':
    case 'admin':
    case 'system':
      return '/officer';
    case 'extension_worker':
      return '/officer/extension';
    default:
      return '/farmer';
  }
}

export const LoginPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const lang = (i18n.language || 'en').slice(0, 2);
  const { loginFn, user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // If user is already authenticated, redirect to target or role home
  useEffect(() => {
    if (isAuthenticated && user) {
      const fromLocation = (location.state as { from?: { pathname?: string } })?.from?.pathname;
      const targetPath = fromLocation || getRoleRedirectPath(user.role);
      navigate(targetPath, { replace: true });
    }
  }, [isAuthenticated, user, navigate, location]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    const trimmedIdentifier = identifier.trim();
    if (!trimmedIdentifier) {
      setError(t('login.needIdentifier'));
      return;
    }

    if (!password) {
      setError(t('login.needPassword'));
      return;
    }

    // Build login payload: determine whether identifier is email or phone
    const isEmail = trimmedIdentifier.includes('@');
    const credentials: LoginRequest = {
      password,
      ...(isEmail ? { email: trimmedIdentifier } : { phone: trimmedIdentifier }),
    };

    setIsSubmitting(true);

    try {
      const response = await loginFn(credentials);
      // Determine destination from token or user role
      const role = user?.role;
      const fromLocation = (location.state as { from?: { pathname?: string } })?.from?.pathname;

      if (fromLocation) {
        navigate(fromLocation, { replace: true });
      } else if (role) {
        navigate(getRoleRedirectPath(role), { replace: true });
      } else {
        // Fallback: decode role from the token response directly
        try {
          const payload = JSON.parse(atob(response.access_token.split('.')[1] || '{}'));
          const decodedRole = payload.role as UserRole;
          navigate(getRoleRedirectPath(decodedRole), { replace: true });
        } catch {
          navigate('/farmer', { replace: true });
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError(t('auth.invalidCredentials'));
        } else if (err.status === 0) {
          setError(t('errors.networkError'));
        } else {
          setError(t('login.failed'));
        }
      } else {
        setError(t('errors.unknownError'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isEmailInput = identifier.includes('@');

  return (
    <main className="min-h-screen bg-gradient-to-b from-primary-50/50 via-surface to-surface-raised flex flex-col justify-center items-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* KrishiOS Branding */}
        <header className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 text-white shadow-md shadow-primary-600/20 mb-2">
            <Sprout className="w-8 h-8" aria-hidden="true" />
          </div>
          <h1 className="text-display font-bold text-text tracking-tight">KrishiOS</h1>
          <p className="text-small text-text-secondary max-w-sm mx-auto">{t('shell.tagline')}</p>
          <div className="flex justify-center gap-1.5 pt-1" role="radiogroup" aria-label={t('common.language')}>
            {([['te', 'తెలుగు'], ['hi', 'हिंदी'], ['en', 'English']] as const).map(([code, label]) => (
              <button
                key={code}
                type="button"
                role="radio"
                aria-checked={lang === code}
                onClick={() => void i18n.changeLanguage(code)}
                className={`px-3 py-1 rounded-full border text-caption font-semibold cursor-pointer ${
                  lang === code ? 'bg-primary-600 text-white border-primary-600' : 'bg-surface text-text border-border'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        {/* Login Card */}
        <Card variant="raised" className="bg-surface shadow-lg border-border/80 rounded-xl p-6 sm:p-8">
          <CardHeader className="text-center mb-6">
            <CardTitle as="h2" className="text-heading font-semibold text-text">
              {t('auth.loginButton')}
            </CardTitle>
            <CardDescription className="text-small text-text-secondary">{t('login.subtitle')}</CardDescription>
          </CardHeader>

          <CardContent className="p-0">
            {error && (
              <div
                role="alert"
                className="mb-5 p-3.5 rounded-lg bg-danger-50 border border-danger-100 flex items-start gap-2.5 text-danger-700 animate-fade-in"
              >
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-small font-medium">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <Input
                  id="login-identifier"
                  type={isEmailInput ? 'email' : 'text'}
                  label={t('login.identifier')}
                  placeholder={t('login.identifierHint')}
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  disabled={isSubmitting || isAuthLoading}
                  required
                  autoComplete="username"
                  leftIcon={
                    isEmailInput ? (
                      <Mail className="w-5 h-5" aria-hidden="true" />
                    ) : (
                      <Phone className="w-5 h-5" aria-hidden="true" />
                    )
                  }
                />
              </div>

              <div>
                <Input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  label={t('auth.password')}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting || isAuthLoading}
                  required
                  autoComplete="current-password"
                  leftIcon={<Lock className="w-5 h-5" aria-hidden="true" />}
                  rightElement={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="p-1 text-text-muted hover:text-text focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded"
                      aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
                      tabIndex={0}
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" aria-hidden="true" />
                      ) : (
                        <Eye className="w-4 h-4" aria-hidden="true" />
                      )}
                    </button>
                  }
                />
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  fullWidth
                  isLoading={isSubmitting || isAuthLoading}
                >
                  {t('auth.loginButton')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer info / accessibility note */}
        <footer className="text-center text-caption text-text-muted">
          <p>KrishiOS Platform &copy; {new Date().getFullYear()} — Secure & Private</p>
        </footer>
      </div>
    </main>
  );
};

export default LoginPage;
