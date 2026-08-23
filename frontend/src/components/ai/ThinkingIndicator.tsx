import React from 'react';
import { Loader2, Sparkles } from 'lucide-react';

export interface ThinkingIndicatorProps {
  /** The in-progress status message (default: "Analyzing...") */
  message?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional custom CSS class names */
  className?: string;
  /** Optional secondary detail message, e.g. "Querying satellite telemetry..." */
  detail?: string;
}

/**
 * Accessible indicator showing real-time AI reasoning, data ingestion, or model inference.
 */
export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  message = 'Analyzing...',
  size = 'md',
  className = '',
  detail,
}) => {
  const sizeStyles = {
    sm: {
      container: 'px-2.5 py-1.5 text-xs gap-2',
      icon: 'w-3.5 h-3.5',
      dot: 'w-1.5 h-1.5',
    },
    md: {
      container: 'px-3.5 py-2.5 text-sm gap-2.5',
      icon: 'w-4 h-4',
      dot: 'w-2 h-2',
    },
    lg: {
      container: 'px-4 py-3 text-base gap-3',
      icon: 'w-5 h-5',
      dot: 'w-2.5 h-2.5',
    },
  };

  const currentSize = sizeStyles[size];

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`inline-flex flex-col rounded-lg border border-primary-200/80 bg-primary-50/50 shadow-sm ${className}`}
    >
      <div className={`flex items-center ${currentSize.container}`}>
        {/* Animated Icon */}
        <div className="relative flex items-center justify-center text-primary-600">
          <Loader2 className={`${currentSize.icon} animate-spin`} aria-hidden="true" />
          <Sparkles className="absolute w-2 h-2 text-primary-500 animate-ping opacity-75" aria-hidden="true" />
        </div>

        {/* Text and animated bouncing dots */}
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="font-medium text-text">{message}</span>
          <span className="inline-flex items-center gap-0.5" aria-hidden="true">
            <span
              className={`${currentSize.dot} rounded-full bg-primary-600 animate-bounce`}
              style={{ animationDelay: '0ms', animationDuration: '1s' }}
            />
            <span
              className={`${currentSize.dot} rounded-full bg-primary-600 animate-bounce`}
              style={{ animationDelay: '180ms', animationDuration: '1s' }}
            />
            <span
              className={`${currentSize.dot} rounded-full bg-primary-600 animate-bounce`}
              style={{ animationDelay: '360ms', animationDuration: '1s' }}
            />
          </span>
        </div>
      </div>

      {detail && (
        <div className="border-t border-primary-100/80 px-3.5 py-1.5 text-xs text-text-secondary bg-primary-50/20">
          {detail}
        </div>
      )}
    </div>
  );
};

export default ThinkingIndicator;
