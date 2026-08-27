/**
 * AnalyticsPage Component.
 *
 * Regional agricultural intelligence, outbreak tracking, severe weather
 * alert monitoring, and broadcast advisory event issuance.
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { RiskBadge } from '@/components/ai/RiskBadge';
import { BroadcastEventModal } from '@/features/officer/components/BroadcastEventModal';
import {
  useProactiveDecisions,
  useSevereWeatherAlerts,
  useEmitEvent,
} from '@/features/officer/hooks/useOfficerData';
import {
  CloudRain,
  Radio,
  Activity,
  CheckCircle2,
} from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [isBroadcastOpen, setIsBroadcastOpen] = useState(false);

  const { data: decisions = [], isLoading: isDecisionsLoading } = useProactiveDecisions();
  const { data: weatherAlerts = [], isLoading: isWeatherLoading } = useSevereWeatherAlerts();
  const emitEventMutation = useEmitEvent();

  const isLoading = isDecisionsLoading || isWeatherLoading;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">
            Regional Risk Radar &amp; Analytics
          </h1>
          <p className="text-body text-text-secondary">
            Monitor district outbreak clusters, severe weather events, and proactive decision volume
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => setIsBroadcastOpen(true)}
          className="cursor-pointer self-start sm:self-auto"
        >
          <Radio className="w-4 h-4 mr-1.5" aria-hidden="true" />
          <span>Issue Emergency Broadcast</span>
        </Button>
      </div>

      {/* Severe Weather Alert Monitor */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <CloudRain className="w-5 h-5 text-info-600" aria-hidden="true" />
          <h2 className="text-subheading font-bold text-text">
            Active Meteorological Warnings ({weatherAlerts.length})
          </h2>
        </div>

        {weatherAlerts.length === 0 ? (
          <Card variant="raised" padding="md" className="flex items-center gap-3 bg-surface">
            <CheckCircle2 className="w-5 h-5 text-success-600 flex-shrink-0" aria-hidden="true" />
            <span className="text-small text-text">No active severe weather warnings in this district.</span>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {weatherAlerts.map((alert) => (
              <Card
                key={alert.alert_id}
                variant="default"
                padding="md"
                className="border-l-4 border-l-danger-500 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-caption font-bold uppercase text-danger-700 bg-danger-50 px-2 py-0.5 rounded">
                    {alert.severity} • {alert.event_type}
                  </span>
                  <span className="text-caption text-text-muted">
                    Until {new Date(alert.effective_until).toLocaleDateString()}
                  </span>
                </div>
                <h3 className="text-body font-bold text-text">{alert.headline}</h3>
                <p className="text-small text-text-secondary">{alert.instruction}</p>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Proactive Risk Outbreak Decisions Feed */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-600" aria-hidden="true" />
          <h2 className="text-subheading font-bold text-text">
            Recent Proactive Decision Intelligence ({decisions.length})
          </h2>
        </div>

        <div className="space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              <Card variant="default" padding="md">
                <Skeleton width="40%" height={20} />
                <Skeleton height={50} className="mt-2" />
              </Card>
            </div>
          ) : decisions.length === 0 ? (
            <Card variant="default" padding="lg" className="text-center py-10 text-text-muted">
              <p className="text-small">No recent automated decision records generated.</p>
            </Card>
          ) : (
            decisions.slice(0, 10).map((d) => (
              <Card key={d.decision_id} variant="default" padding="md" className="space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <RiskBadge severity={d.risk_severity} size="sm" />
                    <span className="text-small font-bold text-text">{d.risk_type}</span>
                    <span className="text-caption text-text-muted">
                      • Farmer #{d.farmer_id || 'Broadcast'}
                    </span>
                  </div>
                  <span className="text-caption text-text-muted">
                    Confidence: {Math.round(d.confidence * 100)}%
                  </span>
                </div>
                <p className="text-small text-text whitespace-pre-line leading-relaxed">
                  {d.advisory_text}
                </p>
              </Card>
            ))
          )}
        </div>
      </section>

      {/* Broadcast Modal */}
      <BroadcastEventModal
        isOpen={isBroadcastOpen}
        onClose={() => setIsBroadcastOpen(false)}
        onEmitEvent={async (payload) => {
          return await emitEventMutation.mutateAsync(payload);
        }}
      />
    </div>
  );
};

export default AnalyticsPage;
