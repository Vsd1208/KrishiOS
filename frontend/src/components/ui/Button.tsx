/**
 * @file Button.tsx
 * @description Reusable, accessible button component for KrishiOS.
 *
 * Supports multiple visual variants (primary, secondary, outline, ghost, danger),
 * sizes (sm, md, lg), and loading states with an integrated accessible spinner.
 * Fully keyboard-navigable with clear focus-visible rings and ARIA support.
 */

import React, { forwardRef } from 'react';
import { Spinner } from './Spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: ButtonVariant;
  /** Size modifier */
  size?: ButtonSize;
  /** Whether the button should stretch full-width */
  fullWidth?: boolean;
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Custom spinner label when loading */
  loadingText?: string;
  /** Icon or element to render before button children */
  leftIcon?: React.ReactNode;
  /** Icon or element to render after button children */
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 text-text-inverse hover:bg-primary-700 active:bg-primary-800 shadow-sm border border-transparent focus-visible:ring-primary-500',
  secondary:
    'bg-surface-raised text-text hover:bg-border/50 active:bg-border border border-border shadow-sm focus-visible:ring-primary-500',
  outline:
    'bg-transparent text-primary-600 border border-primary-600 hover:bg-primary-50 active:bg-primary-100 focus-visible:ring-primary-500',
  ghost:
    'bg-transparent text-text-secondary hover:text-text hover:bg-surface-raised active:bg-border/30 border border-transparent focus-visible:ring-primary-500',
  danger:
    'bg-danger-600 text-text-inverse hover:bg-danger-700 active:bg-danger-700 shadow-sm border border-transparent focus-visible:ring-danger-500',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'text-caption font-medium px-3 py-1.5 gap-1.5 rounded min-h-[32px]',
  md: 'text-small font-medium px-4 py-2 gap-2 rounded-md min-h-[40px]',
  lg: 'text-body font-medium px-5 py-2.5 gap-2.5 rounded-lg min-h-[48px]',
};

const spinnerSizeMap: Record<ButtonSize, 'sm' | 'md' | 'lg'> = {
  sm: 'sm',
  md: 'sm',
  lg: 'md',
};

/**
 * Button component supporting various states, styles, and accessibility attributes.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      isLoading = false,
      loadingText,
      disabled = false,
      leftIcon,
      rightIcon,
      className = '',
      children,
      type = 'button',
      ...restProps
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;
    const baseStyles =
      'inline-flex items-center justify-center font-sans transition-colors duration-150 select-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';
    const stateStyles = isDisabled
      ? 'opacity-60 cursor-not-allowed pointer-events-none'
      : '';
    const widthStyles = fullWidth ? 'w-full' : '';

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={isLoading ? 'true' : undefined}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthStyles} ${stateStyles} ${className}`.trim()}
        {...restProps}
      >
        {isLoading ? (
          <>
            <Spinner
              size={spinnerSizeMap[size]}
              color={variant === 'primary' || variant === 'danger' ? 'white' : 'primary'}
              label={loadingText || (typeof children === 'string' ? `Loading ${children}` : 'Loading...')}
            />
            {loadingText && <span>{loadingText}</span>}
          </>
        ) : (
          <>
            {leftIcon && <span className="inline-flex shrink-0 items-center">{leftIcon}</span>}
            {children}
            {rightIcon && <span className="inline-flex shrink-0 items-center">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
