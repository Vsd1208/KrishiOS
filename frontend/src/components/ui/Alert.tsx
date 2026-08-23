/**
 * @file Alert.tsx
 * @description Semantic notification and alert banner component for KrishiOS.
 *
 * Communicates status, warnings, errors, and informational feedback.
 * Uses appropriate ARIA roles (`role="alert"` for high urgency, `role="status"` for info/success)
 * and includes dismiss capability with keyboard accessibility.
 */

import React, { forwardRef } from 'react';
import { Info, CheckCircle, AlertTriangle, XCircle, X } from 'lucide-react';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

export interface AlertProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Visual severity variant */
  variant?: AlertVariant;
  /** Optional alert title heading */
  title?: React.ReactNode;
  /** Optional custom icon override */
  icon?: React.ReactNode;
  /** Callback fired when the dismiss button is clicked */
  onDismiss?: () => void;
}

const variantConfig: Record<
  AlertVariant,
  {
    containerStyle: string;
    iconColor: string;
    titleColor: string;
    textColor: string;
    defaultIcon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
    role: 'alert' | 'status';
  }
> = {
  info: {
    containerStyle: 'bg-info-50 border-info-100 text-info-700',
    iconColor: 'text-info-600',
    titleColor: 'text-info-700 font-semibold',
    textColor: 'text-info-700',
    defaultIcon: Info,
    role: 'status',
  },
  success: {
    containerStyle: 'bg-success-50 border-success-100 text-success-700',
    iconColor: 'text-success-600',
    titleColor: 'text-success-700 font-semibold',
    textColor: 'text-success-700',
    defaultIcon: CheckCircle,
    role: 'status',
  },
  warning: {
    containerStyle: 'bg-warning-50 border-warning-100 text-warning-700',
    iconColor: 'text-warning-600',
    titleColor: 'text-warning-700 font-semibold',
    textColor: 'text-warning-700',
    defaultIcon: AlertTriangle,
    role: 'alert',
  },
  error: {
    containerStyle: 'bg-danger-50 border-danger-100 text-danger-700',
    iconColor: 'text-danger-600',
    titleColor: 'text-danger-700 font-semibold',
    textColor: 'text-danger-700',
    defaultIcon: XCircle,
    role: 'alert',
  },
};

/**
 * Alert banner component for warnings, errors, successes, and information.
 */
export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      variant = 'info',
      title,
      icon,
      onDismiss,
      children,
      className = '',
      ...restProps
    },
    ref
  ) => {
    const config = variantConfig[variant];
    const IconComponent = config.defaultIcon;

    return (
      <div
        ref={ref}
        role={config.role}
        aria-live={config.role === 'alert' ? 'assertive' : 'polite'}
        className={`flex items-start gap-3 p-4 rounded-lg border text-small transition-all duration-150 ${config.containerStyle} ${className}`.trim()}
        {...restProps}
      >
        <span className={`shrink-0 mt-0.5 ${config.iconColor}`}>
          {icon ?? <IconComponent className="w-5 h-5" aria-hidden="true" />}
        </span>

        <div className="flex-1 flex flex-col gap-1 min-w-0">
          {title && <h4 className={`text-small leading-5 ${config.titleColor}`}>{title}</h4>}
          {children && (
            <div className={`text-small leading-relaxed ${config.textColor}`}>
              {children}
            </div>
          )}
        </div>

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss alert"
            className="shrink-0 p-1 -mr-1 -mt-1 rounded-md text-text-secondary hover:text-text hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 transition-colors"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </div>
    );
  }
);

Alert.displayName = 'Alert';
