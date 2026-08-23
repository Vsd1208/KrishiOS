/**
 * @file Input.tsx
 * @description Accessible text input field with integrated label, helper text, and error handling.
 *
 * Automatically links labels with inputs via unique identifiers, handles aria-describedby
 * for error messages and helper notes, and applies visual validation states.
 */

import React, { forwardRef, useId } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Label text displayed above the input */
  label?: string;
  /** Error message displayed below the input in red */
  error?: string;
  /** Informational helper text displayed below the input */
  helperText?: string;
  /** Optional icon or decorative element on the left side of the input */
  leftIcon?: React.ReactNode;
  /** Optional icon or action element on the right side of the input */
  rightIcon?: React.ReactNode;
  /** Element placed on the left side */
  leftElement?: React.ReactNode;
  /** Element placed on the right side (e.g. eye toggle button) */
  rightElement?: React.ReactNode;
  /** Additional class names for the outer container */
  containerClassName?: string;
}

/**
 * Form input component with full accessibility, label, helper text, and error indicators.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      id,
      leftIcon,
      rightIcon,
      leftElement,
      rightElement,
      disabled = false,
      required = false,
      className = '',
      containerClassName = '',
      ...restProps
    },
    ref
  ) => {
    const finalLeft = leftElement || leftIcon;
    const finalRight = rightElement || rightIcon;
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    // Construct aria-describedby based on available hints/errors
    const describedBy = [
      error ? errorId : null,
      helperText && !error ? helperId : null,
    ]
      .filter(Boolean)
      .join(' ') || undefined;

    const hasError = Boolean(error);

    const baseInputStyles =
      'w-full block rounded-md text-body font-sans transition-colors duration-150 placeholder:text-text-muted disabled:bg-surface-raised disabled:text-text-muted disabled:cursor-not-allowed';

    const borderStyles = hasError
      ? 'border-danger-500 text-danger-900 focus:border-danger-600 focus:ring-2 focus:ring-danger-500/20 bg-surface'
      : 'border-border text-text bg-surface hover:border-border-strong focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20';

    const paddingStyles = `${finalLeft ? 'pl-10' : 'pl-3.5'} ${
      finalRight ? 'pr-10' : 'pr-3.5'
    } py-2`;

    return (
      <div className={`w-full flex flex-col gap-1.5 ${containerClassName}`.trim()}>
        {label && (
          <label
            htmlFor={inputId}
            className="text-small font-medium text-text flex items-center justify-between select-none"
          >
            <span>
              {label}
              {required && <span className="text-danger-500 ml-1" aria-hidden="true">*</span>}
            </span>
          </label>
        )}

        <div className="relative flex items-center w-full">
          {finalLeft && (
            <div className="absolute left-3 flex items-center text-text-muted shrink-0 z-10">
              {finalLeft}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            required={required}
            aria-invalid={hasError ? 'true' : 'false'}
            aria-describedby={describedBy}
            className={`border ${baseInputStyles} ${borderStyles} ${paddingStyles} ${className}`.trim()}
            {...restProps}
          />

          {finalRight && (
            <div className="absolute right-3 flex items-center text-text-muted shrink-0 z-10">
              {finalRight}
            </div>
          )}
        </div>

        {hasError ? (
          <p
            id={errorId}
            role="alert"
            className="text-caption text-danger-600 font-medium flex items-center gap-1 mt-0.5"
          >
            {error}
          </p>
        ) : helperText ? (
          <p
            id={helperId}
            className="text-caption text-text-secondary mt-0.5"
          >
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
