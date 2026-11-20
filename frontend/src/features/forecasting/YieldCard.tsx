/**
 * One district yield forecast: the estimate, its likely range and the normal yield, or a plain
 * "insufficient data" abstention with no number. Always labelled as a model estimate, never as
 * an official crop-cutting, YES-TECH or insurance figure.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Sprout } from 'lucide-react';

import type { YieldForecast } from '@/services/api/forecasting';
import { cropName, modalityList, reviewReasons, unitLabel } from './format';
import { YieldRangeBar } from './YieldRangeBar';

const n2 = (v: number | null) => (v === null ? '—' : v.toFixed(2));

export const YieldCard: React.FC<{ forecast: YieldForecast; compact?: boolean }> = ({ forecast: f, compact }) => {
  const { t, i18n } = useTranslation();
  const name = cropName(f, i18n.language);
  const season = `${t(`yieldx.season.${f.season}`, { defaultValue: f.season })} ${f.crop_year}-${String(f.crop_year + 1).slice(-2)}`;
  const change = f.change_vs_normal;
  const reasons = reviewReasons(f);
  const hasBar =
    f.predicted_yield !== null && f.interval_low !== null && f.interval_high !== null && f.normal_yield !== null;

  return (
    <section
      aria-label={t('yieldx.cardTitle', { crop: name })}
      className="rounded-xl border border-border bg-surface p-3 space-y-1.5"
      data-testid="yield-card"
    >
      <h3 className="flex items-center gap-1.5 text-caption font-bold uppercase text-text-secondary">
        <Sprout className="w-3.5 h-3.5" aria-hidden="true" />
        {t('yieldx.cardTitle', { crop: name })} · {season}
      </h3>
      {f.abstained ? (
        <p className="text-small text-text-muted">{t('yieldx.abstain')}</p>
      ) : (
        <>
          <p className="text-heading font-extrabold text-text">
            {n2(f.predicted_yield)} <span className="text-small font-normal">{unitLabel(f.unit)}</span>
          </p>
          <p className="text-caption text-text-secondary">
            {t('yieldx.range', { low: n2(f.interval_low), high: n2(f.interval_high) })} ·{' '}
            {t('yieldx.normal', { normal: n2(f.normal_yield), unit: unitLabel(f.unit) })}
          </p>
          {hasBar && (
            <YieldRangeBar
              low={f.interval_low!}
              high={f.interval_high!}
              forecast={f.predicted_yield!}
              normal={f.normal_yield!}
              shortfall={f.likely_shortfall}
              legend={!compact}
            />
          )}
          {!compact && <p className="text-caption text-text-muted">{t('yieldx.rangeMeaning')}</p>}
          {change !== null && (
            <p className={`text-small font-semibold ${f.likely_shortfall ? 'text-red-700' : 'text-text'}`}>
              {Math.abs(change) < 0.05
                ? t('yieldx.nearNormal')
                : change < 0
                  ? t('yieldx.below', { pct: Math.round(-change * 100) })
                  : t('yieldx.above', { pct: Math.round(change * 100) })}
              {f.likely_shortfall ? ` · ${t('yieldx.likelyShortfall')}` : ''}
            </p>
          )}
          {f.requires_human_review && (
            <div className="space-y-0.5 text-caption text-amber-800">
              <p className="flex items-start gap-1">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                {t('yieldx.review', { tier: f.crop_tier })}
              </p>
              {reasons.length > 0 && (
                <ul className="list-disc pl-6" data-testid="yield-review-reasons">
                  {reasons.map((r) => (
                    <li key={r}>{t(`yieldx.why.${r}`, { list: modalityList(f.missing_modalities, t) })}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
      {!compact && (
        <p className="text-caption text-text-muted">
          {t('yieldx.provenance', { model: f.model_name, version: f.model_version, lead: f.forecast_lead })}
        </p>
      )}
      <p className="text-caption text-text-muted">{t('yieldx.notOfficial')}</p>
    </section>
  );
};

export default YieldCard;
