/**
 * F15 insurance helper (Phase 8): PMFBY guidance (premium, enrolment, crop-loss intimation),
 * shown once an officer has verified it against official sources, plus the district yield
 * outlook as context, labelled as a model estimate and not a YES-TECH or claim figure.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ExternalLink, ShieldCheck } from 'lucide-react';

import { DistrictPicker } from '@/features/govconnect/DistrictPicker';
import { YieldCard } from '@/features/forecasting/YieldCard';
import { forecastingApi } from '@/services/api/forecasting';

export const InsurancePage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const language = (['en', 'hi', 'te'].includes(i18n.language) ? i18n.language : 'en') as string;
  const [lgd, setLgd] = useState<number | null>(null);
  const [crop, setCrop] = useState('');
  const helper = useQuery({
    queryKey: ['insurance', lgd, crop, language],
    queryFn: () => forecastingApi.insurance({ lgd, crop: crop.trim() || null, language }),
  });
  const h = helper.data;

  return (
    <div className="space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-heading font-bold text-text">
        <ShieldCheck className="w-5 h-5 text-primary-600" aria-hidden="true" />
        {t('insurance.title')}
      </h1>
      <p className="text-small text-text-secondary">{t('insurance.intro')}</p>

      {h && h.status !== 'verified' && h.guidance.length === 0 && (
        <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-small text-amber-900">
          {t('insurance.pending')}
        </p>
      )}

      {h && h.guidance.length > 0 && (
        <ul className="space-y-2">
          {h.guidance.map((g) => (
            <li key={g.id} className="rounded-xl border border-border bg-surface p-3 space-y-1">
              <p className="text-small text-text">{g.text}</p>
              <a
                href={g.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-caption text-primary-700 hover:underline"
              >
                {g.source} <ExternalLink className="w-3 h-3" aria-hidden="true" />
              </a>
              {g.needs_official_source && (
                <p className="text-caption text-amber-800">{t('insurance.toVerify', { note: g.needs_official_source })}</p>
              )}
            </li>
          ))}
        </ul>
      )}

      <a
        href={h?.official_portal ?? 'https://pmfby.gov.in/'}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-small font-semibold text-primary-700 hover:underline"
      >
        {t('insurance.portal')} <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
      </a>

      <section className="space-y-2 rounded-2xl border border-border bg-surface-raised p-3">
        <h2 className="text-caption font-bold uppercase text-text-secondary">{t('insurance.yieldTitle')}</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-64">
            <DistrictPicker onPick={(d) => setLgd(d.lgd_district_code)} />
          </div>
          <label className="text-caption text-text-secondary">
            {t('insurance.crop')}
            <input
              value={crop}
              onChange={(e) => setCrop(e.target.value)}
              placeholder={t('insurance.cropPlaceholder')}
              className="block mt-1 w-48 rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
            />
          </label>
        </div>
        {h?.yield_context ? (
          <>
            <YieldCard forecast={h.yield_context} compact />
            <p className="text-caption font-semibold text-text-secondary">{h.yield_context.notice}</p>
          </>
        ) : (
          lgd && crop.trim() && <p className="text-small text-text-muted">{t('insurance.noYield')}</p>
        )}
      </section>
    </div>
  );
};

export default InsurancePage;
