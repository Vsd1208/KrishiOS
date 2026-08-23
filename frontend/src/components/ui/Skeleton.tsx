/**
 * @file Skeleton.tsx
 * @description Animated placeholder skeleton component for content loading states.
 *
 * Provides placeholder blocks or circles with a pulsing animation to indicate
 * where async content will appear, improving perceived load performance.
 */

import React, { forwardRef } from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Explicit width (e.g. '100px', '50%', 'w-full') or number in pixels */
  width?: string | number;
  /** Explicit height (e.g. '20px', 'h-4') or number in pixels */
  height?: string | number;
  /** Whether the shape should be rounded, or specify border radius */
  rounded?: boolean | 'none' | 'sm' | 'md' | 'lg' | 'full';
  /** Shortcut for creating circular skeleton avatars/icons */
  circle?: boolean;
  /** Whether the pulse animation is active */
  animate?: boolean;
  /** Whether the skeleton is displayed inline */
  inline?: boolean;
}

const roundedStyles: Record<string, string> = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

/**
 * Skeleton placeholder loader component.
 */
export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  (
    {
      width,
      height,
      rounded = true,
      circle = false,
      animate = true,
      inline = false,
      className = '',
      style,
      ...restProps
    },
    ref
  ) => {
    // Resolve border radius
    let borderRadiusClass = 'rounded-md';
    if (circle) {
      borderRadiusClass = 'rounded-full';
    } else if (typeof rounded === 'string') {
      borderRadiusClass = roundedStyles[rounded] || 'rounded-md';
    } else if (rounded === false) {
      borderRadiusClass = 'rounded-none';
    }

    const inlineStyle: React.CSSProperties = {
      ...(width !== undefined
        ? { width: typeof width === 'number' ? `${width}px` : width }
        : {}),
      ...(height !== undefined
        ? { height: typeof height === 'number' ? `${height}px` : height }
        : {}),
      ...style,
    };

    const displayClass = inline ? 'inline-block align-middle' : 'block';
    const animationClass = animate ? 'animate-pulse' : '';

    return (
      <div
        ref={ref}
        role="presentation"
        aria-hidden="true"
        style={inlineStyle}
        className={`${displayClass} ${animationClass} ${borderRadiusClass} bg-border/80 ${className}`.trim()}
        {...restProps}
      />
    );
  }
);

Skeleton.displayName = 'Skeleton';
