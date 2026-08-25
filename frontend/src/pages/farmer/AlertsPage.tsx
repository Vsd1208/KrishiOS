/**
 * AlertsPage Component.
 *
 * Comprehensive view of active crop risk warnings, weather advisories,
 * disease detections, and officer-reviewed notifications with 1-click acknowledge.
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { AlertCard } from '@/features/farmer/components/AlertCard';
import {
  useFarmerProfile,
  useFarmerAlerts,
  useCropAdvisories,
} from '@/features/farmer/hooks/useFarmerData';
import { CheckCircle2, BookOpen } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'active' | 'all'>('active');

  const { data: farmer } = useFarmerProfile();
  const { alerts, isLoading, acknowledgeAlert, isAcknowledging } = useFarmerAlerts(farmer?.id);
  const { data: advisories = [] } = useCropAdvisories('Paddy', farmer?.village || 'Khammam');

  const unacknowledgedAlerts = alerts.filter((a) => a.status !== 'ACKNOWLEDGED');
  const displayedAlerts = activeTab === 'active' ? unacknowledgedAlerts : alerts;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">
            Advisories &amp; Risk Alerts
          </h1>
          <p className="text-body text-text-secondary">
            Real-time pest, meteorological, and crop protection notifications
          </p>
        </div>

        {/* Tab Filters */}
        <div className="flex p-1 rounded-xl bg-surface border border-border self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveTab('active')}
            className={`px-4 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
              activeTab === 'active'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-text-secondary hover:text-text'
            }`}
          >
            Active ({unacknowledgedAlerts.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`px-4 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
              activeTab === 'all'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-text-secondary hover:text-text'
            }`}
          >
            All Alerts ({alerts.length})
          </button>
        </div>
      </div>

      {/* Alerts Feed */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            <Card variant="default" padding="md">
              <Skeleton width="40%" height={20} />
              <Skeleton width="80%" height={16} className="mt-2" />
            </Card>
            <Card variant="default" padding="md">
              <Skeleton width="40%" height={20} />
              <Skeleton width="80%" height={16} className="mt-2" />
            </Card>
          </div>
        ) : displayedAlerts.length === 0 ? (
          <Card variant="raised" padding="lg" className="text-center py-12 space-y-3">
            <div className="w-12 h-12 rounded-full bg-success-50 text-success-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-subheading font-bold text-text">No active alerts</h3>
              <p className="text-small text-text-secondary mt-1">
                Your farm conditions and weather are currently stable.
              </p>
            </div>
          </Card>
        ) : (
          displayedAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={acknowledgeAlert}
              isAcknowledging={isAcknowledging}
            />
          ))
        )}
      </div>

      {/* ICAR Official Agromet Advisories Section */}
      {advisories.length > 0 && (
        <section aria-label="Official ICAR Advisories" className="space-y-3 pt-4 border-t border-border">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <h2 className="text-subheading font-bold text-text">
              Official ICAR Agromet Bulletin
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {advisories.map((adv, idx) => (
              <Card key={idx} variant="default" padding="md" className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-small font-bold text-text">{adv.title}</span>
                  <span className="text-caption text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full font-medium">
                    {adv.issuing_authority}
                  </span>
                </div>
                <p className="text-small text-text-secondary whitespace-pre-line leading-relaxed">
                  {adv.content}
                </p>
                {adv.recommended_practices && adv.recommended_practices.length > 0 && (
                  <div className="pt-2 border-t border-border space-y-1">
                    <span className="text-caption font-bold text-text-muted uppercase block">
                      Recommended Practices:
                    </span>
                    <ul className="list-disc list-inside text-caption text-text space-y-0.5">
                      {adv.recommended_practices.map((practice, pIdx) => (
                        <li key={pIdx}>{practice}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default AlertsPage;
