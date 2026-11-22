/**
 * ErrorState: a friendly, translated error message for a status code, with an optional retry.
 * It never shows stack traces.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
  statusCode?: number;
  fullPage?: boolean;
  className?: string;
}

/** The translation key pair (title, message) for a status code. */
function statusKey(statusCode?: number): string {
  if (statusCode === 0) return 'offline';
  if (statusCode === 401) return 'session';
  if (statusCode === 403) return 'denied';
  if (statusCode === 404) return 'missing';
  if (statusCode !== undefined && statusCode >= 500) return 'server';
  return 'generic';
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  onRetry,
  retryLabel,
  statusCode,
  fullPage = false,
  className = '',
}) => {
  const { t } = useTranslation();
  const key = statusKey(statusCode);

  const content = (
    <div
      className={`flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="w-12 h-12 rounded-full bg-danger-50 text-danger-600 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6" aria-hidden="true" />
      </div>
      <h2 className="text-subheading font-semibold text-text mb-2">{title || t(`errorState.${key}.title`)}</h2>
      <p className="text-small text-text-secondary mb-6 leading-relaxed">{message || t(`errorState.${key}.message`)}</p>
      {onRetry && (
        <Button variant="primary" size="md" onClick={onRetry} leftIcon={<RefreshCw className="w-4 h-4" aria-hidden="true" />}>
          {retryLabel || t('errors.retry')}
        </Button>
      )}
    </div>
  );

  if (fullPage) {
    return <main className="min-h-screen w-full flex items-center justify-center bg-surface p-4">{content}</main>;
  }
  return content;
};

export default ErrorState;
