/**
 * Official mandi price and 30-day trend (AGMARKNET via data.gov.in). Every number on this card
 * comes from the official data or the PIB MSP release; when there is no data it says so.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { TrendingDown, TrendingUp } from 'lucide-react';

import { apiClient } from '@/services/api/client';

export interface MandiTrend {
  crop: string | null;
  district: string;
  points: { date: string; median_modal: number; markets: number }[];
  latest: { date: string; median_modal: number; markets: number } | null;
  change_7d_pct: number | null;
  sharp: boolean;
  stale?: boolean;
  days_since_latest?: number | null;
  msp: number | null;
  source?: string;
}

const inr = (v: number) => `₹${Math.round(v).toLocaleString('en-IN')}`;

export const MandiTrendCard: React.FC<{ crop?: string; district?: string | null }> = ({
  crop,
  district,
}) => {
  const { t, i18n } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ['market', 'trend', crop, district],
    queryFn: () =>
      apiClient.get<MandiTrend>(
        `/live/market/trend?commodity=${encodeURIComponent(crop ?? '')}&district=${encodeURIComponent(district ?? '')}&days=30`,
      ),
    enabled: Boolean(crop && district),
    staleTime: 60 * 60 * 1000,
  });

  if (!crop || !district) {
    return (
      <section className="rounded-2xl border border-border bg-surface p-4">
        <h2 className="text-caption font-bold uppercase text-text-secondary">{t('mandi.title')}</h2>
        <p className="pt-2 text-small text-text-muted">{t('mandi.needCrop')}</p>
      </section>
    );
  }

  const points = data?.points ?? [];
  const max = Math.max(...points.map((p) => p.median_modal), data?.msp ?? 0, 1);
  const min = Math.min(...points.map((p) => p.median_modal), data?.msp ?? Infinity);
  const span = Math.max(max - min, 1);
  const change = data?.change_7d_pct;
  const Arrow = change !== null && change !== undefined && change < 0 ? TrendingDown : TrendingUp;

  return (
    <section
      aria-label={t('mandi.title')}
      className="rounded-2xl border border-border bg-surface p-4 space-y-2"
    >
      <h2 className="text-caption font-bold uppercase text-text-secondary">
        {t('mandi.title')} · {crop} · {district}
      </h2>
      {isLoading ? (
        <p className="text-small text-text-muted">{t('extension.loading')}</p>
      ) : !data?.latest ? (
        <p className="text-small text-text-muted">{t('mandi.noData', { crop, district })}</p>
      ) : (
        <>
          <p className="text-heading font-extrabold text-text">
            {inr(data.latest.median_modal)} <span className="text-small font-normal">/ {t('mandi.quintal')}</span>
          </p>
          <p className="text-caption text-text-secondary">
            {t('mandi.median', { n: data.latest.markets })} ·{' '}
            {new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' }).format(new Date(data.latest.date))}
          </p>
          {data.stale && (
            <p className="text-caption text-amber-800">
              {t('mandi.stale', { days: data.days_since_latest ?? '?' })}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 text-caption">
            {change !== null && change !== undefined ? (
              <span
                className={`flex items-center gap-1 font-semibold ${
                  change >= 0 ? 'text-success-700' : 'text-danger-700'
                }`}
              >
                <Arrow className="w-3.5 h-3.5" aria-hidden="true" />
                {t('mandi.change', { pct: `${change > 0 ? '+' : ''}${change}` })}
              </span>
            ) : (
              <span className="text-text-muted">{t('mandi.noChange')}</span>
            )}
            <span className="text-text-muted">
              {data.msp ? t('mandi.msp', { msp: inr(data.msp) }) : t('mandi.noMsp')}
            </span>
          </div>
          {points.length > 1 && (
            <svg
              role="img"
              aria-label={t('mandi.chart', { days: 30 })}
              viewBox={`0 0 ${points.length * 6} 40`}
              preserveAspectRatio="none"
              className="w-full h-10"
            >
              {data.msp && (
                <line
                  x1="0"
                  x2={points.length * 6}
                  y1={38 - ((data.msp - min) / span) * 34}
                  y2={38 - ((data.msp - min) / span) * 34}
                  className="stroke-amber-500"
                  strokeDasharray="3 2"
                  strokeWidth="0.8"
                />
              )}
              <polyline
                fill="none"
                className="stroke-info-600"
                strokeWidth="1.5"
                points={points
                  .map((p, i) => `${i * 6 + 3},${38 - ((p.median_modal - min) / span) * 34}`)
                  .join(' ')}
              />
            </svg>
          )}
          <p className="text-caption text-text-muted">{t('mandi.source')}</p>
        </>
      )}
    </section>
  );
};
