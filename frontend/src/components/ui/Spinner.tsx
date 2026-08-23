/**
 * @file Spinner.tsx
 * @description Accessible, customizable loading spinner component for KrishiOS.
 *
 * Renders an animated SVG circle with configurable size and color variants.
 * Accessible to screen readers with `role="status"`, `aria-label`, and hidden descriptive text.
 */

import React, { forwardRef } from 'react';

export type SpinnerSize = 'sm' | 'md' | 'lg' | 'xl';
export type SpinnerColor = 'primary' | 'current' | 'white' | 'muted';

export interface SpinnerProps extends React.SVGAttributes<SVGSVGElement> {
  /** Size of the spinner: sm (16px), md (24px), lg (32px), xl (48px) */
  size?: SpinnerSize;
  /** Color theme for the spinner */
  color?: SpinnerColor | string;
  /** Optional variant alias for color */
  variant?: string;
  /** Accessible label for assistive technologies */
  label?: string;
  /** Additional CSS class names */
  className?: string;
}

const sizeDimensions: Record<SpinnerSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
};

const colorStyles: Record<SpinnerColor, string> = {
  primary: 'text-primary-600',
  current: 'text-current',
  white: 'text-text-inverse',
  muted: 'text-text-muted',
};

/**
 * Loading spinner component with rotation animation and screen-reader accessibility.
 */
export const Spinner = forwardRef<SVGSVGElement, SpinnerProps>(
  (
    {
      size = 'md',
      color = 'primary',
      label = 'Loading...',
      className = '',
      ...restProps
    },
    ref
  ) => {
    const resolvedColor = colorStyles[color as SpinnerColor] || 'text-primary-600';

    return (
      <span className="inline-flex items-center justify-center align-middle" role="status" aria-label={label}>
        <svg
          ref={ref}
          className={`animate-spin ${sizeDimensions[size]} ${resolvedColor} ${className}`.trim()}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
          {...restProps}
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span className="sr-only">{label}</span>
      </span>
    );
  }
);

Spinner.displayName = 'Spinner';
