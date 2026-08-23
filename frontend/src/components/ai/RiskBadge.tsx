import React from 'react';
import { Shield, AlertTriangle, AlertOctagon, Siren } from 'lucide-react';
import type { RiskSeverity } from '@/types/proactive';

export interface RiskBadgeProps {
  /** Risk severity level */
  severity: RiskSeverity;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Whether to show the text label */
  showLabel?: boolean;
  /** Additional CSS class names */
  className?: string;
}

interface RiskConfig {
  label: string;
  badgeStyle: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  description: string;
}

const riskConfigs: Record<RiskSeverity, RiskConfig> = {
  LOW: {
    label: 'Low Risk',
    badgeStyle: 'bg-success-50 text-success-700 border-success-200 hover:bg-success-100',
    icon: Shield,
    description: 'Routine monitoring; no immediate hazard detected.',
  },
  MEDIUM: {
    label: 'Medium Risk',
    badgeStyle: 'bg-warning-50 text-warning-700 border-warning-300 hover:bg-warning-100',
    icon: AlertTriangle,
    description: 'Moderate risk detected; advisory precautions recommended.',
  },
  HIGH: {
    label: 'High Risk',
    badgeStyle: 'bg-amber-100 text-amber-900 border-amber-300 font-medium hover:bg-amber-200',
    icon: AlertOctagon,
    description: 'Elevated risk; prompt field inspection or intervention recommended.',
  },
  CRITICAL: {
    label: 'Critical Risk',
    badgeStyle: 'bg-danger-100 text-danger-800 border-danger-300 font-bold animate-pulse-slow hover:bg-danger-200',
    icon: Siren,
    description: 'Severe risk; immediate agricultural or emergency action required.',
  },
};

/**
 * Visual badge indicating agricultural risk severity.
 * Complies with accessibility rules by always combining icons, distinct typography, and text labels (never color alone).
 */
export const RiskBadge: React.FC<RiskBadgeProps> = ({
  severity,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  const config = riskConfigs[severity] || riskConfigs.LOW;
  const IconComponent = config.icon;

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
      title={`Risk level: ${config.label}. ${config.description}`}
      aria-label={`Risk level: ${config.label}`}
      className={`inline-flex items-center rounded-full border transition-colors select-none ${sizeClasses[size]} ${config.badgeStyle} ${className}`}
    >
      <IconComponent className={`${iconSizes[size]} shrink-0`} aria-hidden="true" />
      {showLabel && <span>{config.label}</span>}
    </span>
  );
};

export default RiskBadge;
