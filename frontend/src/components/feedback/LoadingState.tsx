/**
 * LoadingState Component.
 *
 * Accessible loading indicator supporting inline or full-page presentations.
 */

import React from 'react';
import { Spinner } from '@/components/ui/Spinner';

export interface LoadingStateProps {
  message?: string;
  fullPage?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading...',
  fullPage = false,
  size = 'lg',
  className = '',
}) => {
  const content = (
    <div
      className={`flex flex-col items-center justify-center gap-3 p-6 text-center ${className}`}
      role="status"
      aria-live="polite"
    >
      <Spinner size={size} variant="primary" label={message} />
      {message && (
        <p className="text-small font-medium text-text-secondary animate-pulse">
          {message}
        </p>
      )}
      <span className="sr-only">{message}</span>
    </div>
  );

  if (fullPage) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-surface">
        {content}
      </div>
    );
  }

  return content;
};

export default LoadingState;
