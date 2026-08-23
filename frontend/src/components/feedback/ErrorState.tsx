/**
 * ErrorState Component.
 *
 * Friendly error presentation mapping HTTP status codes to actionable messages.
 * Does not expose sensitive stack traces.
 */

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  statusCode?: number;
  fullPage?: boolean;
  className?: string;
}

/**
 * Returns fallback title and user-friendly explanation based on status code.
 */
function getStatusDetails(statusCode?: number): { title: string; message: string } {
  switch (statusCode) {
    case 0:
      return {
        title: 'Connection Issue',
        message: 'Unable to connect to KrishiOS. Please check your internet connection and try again.',
      };
    case 401:
      return {
        title: 'Session Expired',
        message: 'Your session has expired. Please log in again to continue.',
      };
    case 403:
      return {
        title: 'Access Denied',
        message: 'You do not have permission to perform this action or view this resource.',
      };
    case 404:
      return {
        title: 'Page or Resource Not Found',
        message: 'The requested resource could not be found or may have been moved.',
      };
    case 500:
    case 502:
    case 503:
    case 504:
      return {
        title: 'System Temporarily Unavailable',
        message: 'KrishiOS encountered an issue processing your request. Please try again in a few moments.',
      };
    default:
      return {
        title: 'Something Went Wrong',
        message: 'An unexpected error occurred while processing your request.',
      };
  }
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  onRetry,
  statusCode,
  fullPage = false,
  className = '',
}) => {
  const statusDefaults = getStatusDetails(statusCode);
  const displayTitle = title || statusDefaults.title;
  const displayMessage = message || statusDefaults.message;

  const content = (
    <div
      className={`flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="w-12 h-12 rounded-full bg-danger-50 text-danger-600 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6" aria-hidden="true" />
      </div>

      <h2 className="text-subheading font-semibold text-text mb-2">{displayTitle}</h2>

      <p className="text-small text-text-secondary mb-6 leading-relaxed">
        {displayMessage}
      </p>

      {onRetry && (
        <Button
          variant="primary"
          size="md"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-4 h-4" aria-hidden="true" />}
        >
          Try Again
        </Button>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <main className="min-h-screen w-full flex items-center justify-center bg-surface p-4">
        {content}
      </main>
    );
  }

  return content;
};

export default ErrorState;
