/**
 * @file Card.tsx
 * @description Surface container component with structured sub-components and padding options.
 *
 * Utilizes KrishiOS surface design tokens (`bg-surface`, `border-border`, `shadow-card`)
 * with customizable padding scales. Can be used as a simple wrapper or composed with
 * `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter`.
 */

import React, { forwardRef } from 'react';

export type CardPadding = 'none' | 'sm' | 'md' | 'lg';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Internal padding scale */
  padding?: CardPadding;
  /** Optional header slot */
  header?: React.ReactNode;
  /** Optional footer slot */
  footer?: React.ReactNode;
  /** Whether the card has an elevated shadow or subtle border */
  variant?: 'default' | 'raised' | 'overlay' | 'flat';
}

const paddingMap: Record<CardPadding, string> = {
  none: 'p-0',
  sm: 'p-3 sm:p-4',
  md: 'p-4 sm:p-6',
  lg: 'p-6 sm:p-8',
};

const variantMap = {
  default: 'bg-surface border border-border shadow-card',
  raised: 'bg-surface border border-border/80 shadow-raised',
  overlay: 'bg-surface border border-border shadow-overlay',
  flat: 'bg-surface-raised border border-border',
};

/**
 * Main Card surface container.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      padding = 'md',
      variant = 'default',
      header,
      footer,
      className = '',
      ...restProps
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={`rounded-xl transition-shadow duration-150 ${variantMap[variant]} ${paddingMap[padding]} ${className}`.trim()}
        {...restProps}
      >
        {header && <div className="border-b border-border pb-4 mb-4">{header}</div>}
        {children}
        {footer && <div className="border-t border-border pt-4 mt-4">{footer}</div>}
      </div>
    );
  }
);

Card.displayName = 'Card';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Optional action element aligned to the right */
  action?: React.ReactNode;
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ children, action, className = '', ...restProps }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-start justify-between gap-4 pb-4 border-b border-border ${className}`.trim()}
        {...restProps}
      >
        <div className="flex flex-col gap-1">{children}</div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'div';
}

export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ children, as = 'h3', className = '', ...restProps }, ref) => {
    const Component = as as 'h3';
    return (
      <Component
        ref={ref}
        className={`text-subheading font-semibold text-text tracking-tight ${className}`.trim()}
        {...restProps}
      >
        {children}
      </Component>
    );
  }
);

CardTitle.displayName = 'CardTitle';

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  as?: 'p' | 'div' | 'span';
}

export const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ children, as = 'p', className = '', ...restProps }, ref) => {
    const Component = as as 'p';
    return (
      <Component
        ref={ref}
        className={`text-small text-text-secondary ${className}`.trim()}
        {...restProps}
      >
        {children}
      </Component>
    );
  }
);

CardDescription.displayName = 'CardDescription';

export const CardContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, className = '', ...restProps }, ref) => {
    return (
      <div ref={ref} className={`pt-4 ${className}`.trim()} {...restProps}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = 'CardContent';

export const CardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, className = '', ...restProps }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-center justify-end gap-3 pt-4 border-t border-border mt-4 ${className}`.trim()}
        {...restProps}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';
