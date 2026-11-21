/**
 * AlertsPage: the farmer's alerts with one-tap acknowledge, and crop advisories from the advisory
 * service. Advisories are shown only when that service is a live source; a mock or placeholder
 * source is never presented to farmers as an official bulletin.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, BookOpen } from 'lucide-react';

import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { AlertCard } from '@/features/farmer/components/AlertCard';
import {
  useFarmerProfile,
  useFarmerAlerts,
  useCropAdvisories,
  usePrimaryCropName,
} from '@/features/farmer/hooks/useFarmerData';
import { useLiveProvider } from '@/features/farmer/hooks/useLiveProvider';

export const AlertsPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'active' | 'all'>('active');

  const { data: farmer } = useFarmerProfile();
  const { alerts, isLoading, acknowledgeAlert, isAcknowledging } = useFarmerAlerts(farmer?.id);
  const liveAdvisories = useLiveProvider('advisory').isLive;
  const crop = usePrimaryCropName() ?? '';
  const { data: advisories = [] } = useCropAdvisories(liveAdvisories ? crop : '', farmer?.village || undefined);

  const unacknowledged = alerts.filter((a) => a.status !== 'ACKNOWLEDGED');
  const displayed = activeTab === 'active' ? unacknowledged : alerts;
  const tab = (id: 'active' | 'all', label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={activeTab === id}
      onClick={() => setActiveTab(id)}
      className={`px-4 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
        activeTab === id ? 'bg-primary-600 text-white shadow-sm' : 'text-text-secondary hover:text-text'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">{t('alertsPage.title')}</h1>
          <p className="text-body text-text-secondary">{t('alertsPage.subtitle')}</p>
        </div>
        <div className="flex p-1 rounded-xl bg-surface border border-border self-start sm:self-auto" role="tablist">
          {tab('active', t('alertsPage.active', { n: unacknowledged.length }))}
          {tab('all', t('alertsPage.all', { n: alerts.length }))}
        </div>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <Card key={i} variant="default" padding="md">
                <Skeleton width="40%" height={20} />
                <Skeleton width="80%" height={16} className="mt-2" />
              </Card>
            ))}
          </div>
        ) : displayed.length === 0 ? (
          <Card variant="raised" padding="lg" className="text-center py-12 space-y-3">
            <div className="w-12 h-12 rounded-full bg-success-50 text-success-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" aria-hidden="true" />
            </div>
            <h3 className="text-subheading font-bold text-text">{t('alertsPage.none')}</h3>
          </Card>
        ) : (
          displayed.map((alert) => (
            <AlertCard key={alert.id} alert={alert} onAcknowledge={acknowledgeAlert} isAcknowledging={isAcknowledging} />
          ))
        )}
      </div>

      {liveAdvisories && advisories.length > 0 && (
        <section aria-label={t('alertsPage.advisories')} className="space-y-3 pt-4 border-t border-border">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <h2 className="text-subheading font-bold text-text">{t('alertsPage.advisories')}</h2>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {advisories.map((adv, idx) => (
              <Card key={adv.advisory_id ?? idx} variant="default" padding="md" className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-small font-bold text-text">{adv.title}</span>
                  {adv.issuing_authority && (
                    <span className="text-caption text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full font-medium">
                      {adv.issuing_authority}
                    </span>
                  )}
                </div>
                <p className="text-small text-text-secondary whitespace-pre-line leading-relaxed">{adv.content}</p>
                {adv.recommended_practices && adv.recommended_practices.length > 0 && (
                  <div className="pt-2 border-t border-border space-y-1">
                    <span className="text-caption font-bold text-text-muted uppercase block">{t('alertsPage.practices')}</span>
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
