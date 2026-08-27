/**
 * ReviewQueueTable Component.
 *
 * Renders the tabular list of pending advisory notifications requiring
 * expert agricultural sign-off.
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { RiskBadge } from '@/components/ai/RiskBadge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ReviewModal } from '@/features/officer/components/ReviewModal';
import {
  ClipboardCheck,
  User,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import type { AlertNotification, RiskSeverity } from '@/types/proactive';
import type { OfficerReviewActionRequest } from '@/types/officer';

interface ReviewQueueTableProps {
  reviews: AlertNotification[];
  isLoading?: boolean;
  onTakeAction: (alertId: number, payload: OfficerReviewActionRequest) => Promise<void>;
  isActionPending?: boolean;
}

export const ReviewQueueTable: React.FC<ReviewQueueTableProps> = ({
  reviews,
  isLoading,
  onTakeAction,
  isActionPending,
}) => {
  const [selectedAlert, setSelectedAlert] = useState<AlertNotification | null>(null);

  if (isLoading) {
    return (
      <Card variant="default" padding="md" className="space-y-3">
        <Skeleton width="40%" height={24} />
        <Skeleton height={60} />
        <Skeleton height={60} />
        <Skeleton height={60} />
      </Card>
    );
  }

  if (reviews.length === 0) {
    return (
      <Card variant="raised" padding="lg" className="text-center py-12 space-y-3">
        <div className="w-12 h-12 rounded-full bg-success-50 text-success-600 flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-7 h-7" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-subheading font-bold text-text">Review Queue Clear</h3>
          <p className="text-small text-text-secondary mt-1">
            All AI-generated advisories have been verified and processed.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card variant="default" padding="none" className="overflow-hidden border border-border">
        <div className="p-4 bg-surface-raised border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <span className="text-small font-bold text-text uppercase tracking-wider">
              Pending Advisory Queue ({reviews.length})
            </span>
          </div>
          <span className="text-caption text-text-muted">Requires Officer Verification</span>
        </div>

        <div className="divide-y divide-border">
          {reviews.map((alert) => {
            const severity: RiskSeverity =
              alert.priority === 'URGENT'
                ? 'CRITICAL'
                : alert.priority === 'HIGH'
                  ? 'HIGH'
                  : alert.priority === 'NORMAL'
                    ? 'MEDIUM'
                    : 'LOW';

            return (
              <div
                key={alert.id}
                className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-surface-raised/60 transition-colors"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <RiskBadge severity={severity} size="sm" />
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-text-secondary bg-surface px-2 py-0.5 rounded border border-border">
                      <User className="w-3 h-3 text-primary-600" aria-hidden="true" />
                      Farmer #{alert.farmer_id}
                    </span>
                    <span className="text-caption text-text-muted">
                      via {alert.channel}
                    </span>
                  </div>

                  <h3 className="text-body font-bold text-text truncate">{alert.title}</h3>
                  <p className="text-small text-text-secondary line-clamp-2 leading-relaxed">
                    {alert.message}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0 self-end sm:self-center">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setSelectedAlert(alert)}
                    className="cursor-pointer"
                  >
                    <span>Inspect &amp; Verify</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Verification Modal */}
      <ReviewModal
        alert={selectedAlert}
        isOpen={Boolean(selectedAlert)}
        onClose={() => setSelectedAlert(null)}
        onTakeAction={onTakeAction}
        isProcessing={isActionPending}
      />
    </>
  );
};

export default ReviewQueueTable;
