/**
 * AlertCard Component.
 *
 * Renders individual proactive notifications with risk severity badge,
 * plain-language advisory details, officer sign-off verification,
 * and 1-click acknowledgment.
 */

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { RiskBadge } from '@/components/ai/RiskBadge';
import { Check, Bell, ShieldCheck } from 'lucide-react';
import type { AlertNotification, RiskSeverity } from '@/types/proactive';

interface AlertCardProps {
  alert: AlertNotification;
  onAcknowledge?: (alertId: number) => void;
  isAcknowledging?: boolean;
}

export const AlertCard: React.FC<AlertCardProps> = ({
  alert,
  onAcknowledge,
  isAcknowledging,
}) => {
  const isAcknowledged = alert.status === 'ACKNOWLEDGED';

  // Map priority/status to severity indicator
  const severity: RiskSeverity =
    alert.priority === 'URGENT'
      ? 'CRITICAL'
      : alert.priority === 'HIGH'
        ? 'HIGH'
        : alert.priority === 'NORMAL'
          ? 'MEDIUM'
          : 'LOW';

  return (
    <Card
      variant="default"
      padding="md"
      className={`transition-all border-l-4 ${
        isAcknowledged
          ? 'border-l-gray-300 opacity-80 bg-surface'
          : severity === 'CRITICAL' || severity === 'HIGH'
            ? 'border-l-danger-500 bg-danger-50/20'
            : 'border-l-warning-500 bg-warning-50/20'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1.5 flex-1">
          {/* Header Row */}
          <div className="flex items-center gap-2 flex-wrap">
            <RiskBadge severity={severity} size="sm" />
            {isAcknowledged ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                <Check className="w-3 h-3" aria-hidden="true" />
                Acknowledged
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-danger-700 bg-danger-100 px-2 py-0.5 rounded animate-pulse">
                <Bell className="w-3 h-3" aria-hidden="true" />
                Action Required
              </span>
            )}
            {alert.reviewed_by && (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-primary-700 bg-primary-50 px-2 py-0.5 rounded">
                <ShieldCheck className="w-3 h-3 text-primary-600" aria-hidden="true" />
                Officer Verified
              </span>
            )}
          </div>

          {/* Alert Title & Message */}
          <h3 className="text-body font-bold text-text pt-0.5">{alert.title}</h3>
          <p className="text-small text-text-secondary whitespace-pre-line leading-relaxed">
            {alert.message}
          </p>

          {/* Officer Review Note if any */}
          {alert.review_note && (
            <div className="mt-2 p-2 rounded bg-surface border border-border text-caption text-text-secondary">
              <strong className="text-text font-semibold">Officer Note:</strong> {alert.review_note}
            </div>
          )}
        </div>

        {/* Action Button */}
        {!isAcknowledged && onAcknowledge && (
          <div className="sm:self-center flex-shrink-0 pt-2 sm:pt-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onAcknowledge(alert.id)}
              disabled={isAcknowledging}
              className="w-full sm:w-auto"
            >
              {isAcknowledging ? 'Saving...' : 'Acknowledge'}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default AlertCard;
