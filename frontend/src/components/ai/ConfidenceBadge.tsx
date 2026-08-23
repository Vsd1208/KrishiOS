import React from 'react';
import { Shield, ShieldCheck, ShieldAlert } from 'lucide-react';
import type { ConfidenceLevel } from '@/types/proactive';

export interface ConfidenceBadgeProps {
  /** Confidence score between 0 and 1 (e.g. 0.85) */
  confidence: number;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Whether to show text label alongside percentage */
  showLabel?: boolean;
  /** Additional CSS class names */
  className?: string;
}

interface ConfidenceConfig {
  level: ConfidenceLevel;
  label: string;
  badgeStyle: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
}

/**
 * Derives confidence level and presentation config from score (0.0 - 1.0).
 */
const getConfidenceConfig = (score: number): ConfidenceConfig => {
  if (score >= 0.8) {
    return {
      level: 'HIGH',
      label: 'High',
      badgeStyle: 'bg-success-50 text-success-700 border-success-200 hover:bg-success-100',
      icon: ShieldCheck,
    };
  }
  if (score >= 0.5) {
    return {
      level: 'MEDIUM',
      label: 'Medium',
      badgeStyle: 'bg-warning-50 text-warning-700 border-warning-200 hover:bg-warning-100',
      icon: Shield,
    };
  }
  return {
    level: 'LOW',
    label: 'Low',
    badgeStyle: 'bg-danger-50 text-danger-700 border-danger-200 hover:bg-danger-100',
    icon: ShieldAlert,
  };
};

/**
 * Visual badge indicating AI model output confidence score.
 * Never uses color alone: combines icon, numeric percentage, and text labels for accessibility.
 */
export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  // Normalize input in case value is passed as 0-100 instead of 0-1
  const normalized = confidence > 1 ? confidence / 100 : Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(normalized * 100);
  const config = getConfidenceConfig(normalized);
  const IconComponent = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
  };

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
  };

  const tooltipText = `AI confidence: ${percentage}%`;

  return (
    <span
      role="status"
      title={tooltipText}
      aria-label={`${tooltipText} (${config.label} confidence)`}
      className={`inline-flex items-center rounded-full border transition-colors select-none ${sizeClasses[size]} ${config.badgeStyle} ${className}`}
    >
      <IconComponent className={`${iconSizes[size]} shrink-0`} aria-hidden="true" />
      <span className="tabular-nums font-semibold">{percentage}%</span>
      {showLabel && <span className="font-normal opacity-90">{config.label}</span>}
    </span>
  );
};

export default ConfidenceBadge;
