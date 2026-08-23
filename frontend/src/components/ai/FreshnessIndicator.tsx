import React from 'react';
import { Clock, ClockAlert } from 'lucide-react';
import type { FreshnessLevel } from '@/types/proactive';

export interface FreshnessIndicatorProps {
  /** Age of the data in seconds, or undefined if unknown */
  freshnessSeconds: number | undefined;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Whether to render the clock icon */
  showIcon?: boolean;
  /** Additional CSS class names */
  className?: string;
}

interface FreshnessData {
  level: FreshnessLevel;
  displayLabel: string;
  badgeStyle: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  description: string;
}

/**
 * Calculates freshness level, friendly duration string, and styling tokens.
 */
const getFreshnessData = (seconds: number | undefined): FreshnessData => {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) {
    return {
      level: 'UNKNOWN',
      displayLabel: 'Unknown age',
      badgeStyle: 'bg-surface-raised text-text-muted border-border',
      icon: Clock,
      description: 'Data timestamp unavailable',
    };
  }

  // < 1 hour: FRESH
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const timeText = mins <= 1 ? 'Just now' : `${mins}m ago`;
    return {
      level: 'FRESH',
      displayLabel: `Fresh (${timeText})`,
      badgeStyle: 'bg-success-50 text-success-700 border-success-200 hover:bg-success-100',
      icon: Clock,
      description: `Data updated ${timeText} (High freshness)`,
    };
  }

  // < 24 hours: RECENT
  if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600);
    const label = `${hours}h ago`;
    return {
      level: 'RECENT',
      displayLabel: label,
      badgeStyle: 'bg-info-50 text-info-700 border-info-200 hover:bg-info-100',
      icon: Clock,
      description: `Data updated ${hours} hour${hours === 1 ? '' : 's'} ago`,
    };
  }

  // < 3 days (72 hours): STALE
  if (seconds < 259200) {
    const days = Math.floor(seconds / 86400);
    const label = `Stale (${days}d ago)`;
    return {
      level: 'STALE',
      displayLabel: label,
      badgeStyle: 'bg-warning-50 text-warning-700 border-warning-300 font-medium hover:bg-warning-100',
      icon: ClockAlert,
      description: `Warning: Data is ${days} day${days === 1 ? '' : 's'} old and may not reflect current conditions`,
    };
  }

  // >= 3 days: EXPIRED
  const days = Math.floor(seconds / 86400);
  const label = `Expired (${days}d ago)`;
  return {
    level: 'EXPIRED',
    displayLabel: label,
    badgeStyle: 'bg-danger-50 text-danger-700 border-danger-300 font-semibold hover:bg-danger-100',
    icon: ClockAlert,
    description: `Critical: Data is ${days} days old and expired. Refresh telemetry or observations before acting.`,
  };
};

/**
 * Visual indicator for telemetry, weather, and agricultural advisory freshness.
 * Prominently warns users when data is STALE or EXPIRED.
 */
export const FreshnessIndicator: React.FC<FreshnessIndicatorProps> = ({
  freshnessSeconds,
  size = 'md',
  showIcon = true,
  className = '',
}) => {
  const data = getFreshnessData(freshnessSeconds);
  const IconComponent = data.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
  };

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
  };

  return (
    <span
      role="status"
      title={data.description}
      aria-label={`Data freshness: ${data.displayLabel} - ${data.level}`}
      className={`inline-flex items-center rounded-full border transition-colors select-none ${sizeClasses[size]} ${data.badgeStyle} ${className}`}
    >
      {showIcon && (
        <IconComponent className={`${iconSizes[size]} shrink-0`} aria-hidden="true" />
      )}
      <span className="truncate">{data.displayLabel}</span>
    </span>
  );
};

export default FreshnessIndicator;
