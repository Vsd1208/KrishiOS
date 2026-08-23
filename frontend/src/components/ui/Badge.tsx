/**
 * @file Badge.tsx
 * @description Status badge component with semantic color variants and pill styling.
 *
 * Used to indicate statuses, labels, categories, and metrics in agricultural workflows.
 * Supports status indicator dots, custom icons, and small / medium sizes.
 */

import React, { forwardRef } from 'react';

export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'primary';
export type BadgeSize = 'sm' | 'md';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Visual theme variant */
  variant?: BadgeVariant;
  /** Size variant */
  size?: BadgeSize;
  /** Whether to show a leading status dot indicator */
  dot?: boolean;
  /** Optional icon displayed before the label */
  icon?: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-raised text-text-secondary border-border',
  success: 'bg-success-50 text-success-700 border-success-100',
  warning: 'bg-warning-50 text-warning-700 border-warning-100',
  danger: 'bg-danger-50 text-danger-700 border-danger-100',
  info: 'bg-info-50 text-info-700 border-info-100',
  primary: 'bg-primary-50 text-primary-700 border-primary-200',
};

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-text-muted',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-info-500',
  primary: 'bg-primary-500',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'text-caption px-2 py-0.5 gap-1 font-medium',
  md: 'text-small px-2.5 py-1 gap-1.5 font-medium',
};

/**
 * Status badge pill component.
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      icon,
      className = '',
      children,
      ...restProps
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={`inline-flex items-center justify-center rounded-full border leading-tight select-none ${variantStyles[variant]} ${sizeStyles[size]} ${className}`.trim()}
        {...restProps}
      >
        {dot && (
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[variant]}`}
            aria-hidden="true"
          />
        )}
        {icon && <span className="inline-flex shrink-0 items-center text-current">{icon}</span>}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';
