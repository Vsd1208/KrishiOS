/**
 * District yield outlook (Phase 8): every crop's latest imported forecast for a district, with
 * likely shortfalls first. Shortfalls become officer-review advisory drafts in Bulletins; this
 * page never publishes anything. Tier C crops abstain and show no number.
 */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { DistrictPicker } from '@/features/govconnect/DistrictPicker';
import { cropName, unitLabel } from '@/features/forecasting/format';
import { forecastingApi, type Season, type YieldForecast } from '@/services/api/forecasting';

const SEASONS: Season[] = ['Kharif', 'Rabi', 'Zaid', 'Whole Year'];
const n2 = (v: number | null) => (v === null ? '—' : v.toFixed(2));

function sortKey(f: YieldForecast): number {
  if (f.abstained) return 3;
  if (f.likely_shortfall) return 0;
  return f.requires_human_review ? 1 : 2;
}

export const YieldOutlookPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [district, setDistrict] = useState<{ code: number; name: string } | null>(null);
  const [season, setSeason] = useState<Season | ''>('');
  const model = useQuery({ queryKey: ['forecasting', 'model'], queryFn: forecastingApi.model });
  const outlook = useQuery({
    queryKey: ['forecasting', 'outlook', district?.code, season],
    queryFn: () => forecastingApi.outlook(district!.code, season || null),
    enabled: district !== null,
  });
  const runImport = useMutation({
    mutationFn: forecastingApi.runImport,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['forecasting'] }),
  });
  const imp = model.data?.latest_import;
  const items = [...(outlook.data?.items ?? [])].sort((a, b) => sortKey(a) - sortKey(b));

  return (
    <div className="space-y-5">
      <h1 className="text-heading font-bold text-text">{t('yieldx.outlookTitle')}</h1>

      <section className="rounded-2xl border border-border bg-surface p-4 space-y-1 text-caption">
        {imp ? (
          <p className="text-text">
            {t('yieldx.modelLine', {
              model: imp.model_name,
              version: imp.model_version,
              rows: imp.rows,
              date: new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' }).format(new Date(imp.generated_at)),
            })}
          </p>
        ) : (
          <p className="text-text-muted">{t('yieldx.noImport')}</p>
        )}
        <p className="text-text-muted">{t('yieldx.notOfficial')}</p>
        <button
          type="button"
          onClick={() => runImport.mutate()}
          disabled={runImport.isPending}
          className="mt-1 rounded-lg border border-border px-3 py-1 font-semibold text-text hover:border-primary-400 disabled:opacity-50"
        >
          {runImport.isPending ? t('extension.loading') : t('yieldx.import')}
        </button>
        {runImport.data && (
          <p className="text-text-secondary">
            {runImport.data.imported ? t('yieldx.imported') : String(runImport.data.reason ?? t('yieldx.upToDate'))}
          </p>
        )}
      </section>

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-72">
          <DistrictPicker onPick={(d) => setDistrict({ code: d.lgd_district_code, name: d.district_name })} />
        </div>
        <label className="text-caption text-text-secondary">
          {t('yieldx.seasonLabel')}
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value as Season | '')}
            className="block mt-1 rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          >
            <option value="">{t('yieldx.allSeasons')}</option>
            {SEASONS.map((s) => (
              <option key={s} value={s}>
                {t(`yieldx.season.${s}`, { defaultValue: s })}
              </option>
            ))}
          </select>
        </label>
      </div>

      {district && outlook.data && (
        <>
          <p className="text-small text-text">
            <strong>{district.name}</strong> ·{' '}
            {t('yieldx.counts', {
              forecasts: outlook.data.counts.forecasts,
              shortfall: outlook.data.counts.likely_shortfall,
              review: outlook.data.counts.needs_review,
              abstained: outlook.data.counts.abstained,
            })}
            {outlook.data.counts.likely_shortfall > 0 && (
              <>
                {' · '}
                <Link to="/officer/bulletins" className="font-semibold text-primary-700 hover:underline">
                  {t('yieldx.reviewDrafts')}
                </Link>
              </>
            )}
          </p>
          {items.length === 0 ? (
            <p className="text-small text-text-muted">{t('yieldx.noForecasts')}</p>
          ) : (
            <section className="overflow-x-auto rounded-2xl border border-border bg-surface">
              <table className="w-full text-caption">
                <thead className="text-left text-text-muted">
                  <tr>
                    <th className="p-2 font-medium">{t('yieldx.crop')}</th>
                    <th className="p-2 font-medium">{t('yieldx.seasonLabel')}</th>
                    <th className="p-2 font-medium text-right">{t('yieldx.forecast')}</th>
                    <th className="p-2 font-medium text-right">{t('yieldx.rangeCol')}</th>
                    <th className="p-2 font-medium text-right">{t('yieldx.normalCol')}</th>
                    <th className="p-2 font-medium text-right">{t('yieldx.changeCol')}</th>
                    <th className="p-2 font-medium">{t('yieldx.tier')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((f) => (
                    <tr
                      key={`${f.crop_canonical}-${f.season}`}
                      className={`border-t border-border ${f.likely_shortfall ? 'bg-red-50' : ''}`}
                    >
                      <td className="p-2 font-semibold text-text">{cropName(f, i18n.language)}</td>
                      <td className="p-2">
                        {t(`yieldx.season.${f.season}`, { defaultValue: f.season })} {f.crop_year} ·{' '}
                        {t('yieldx.lead', { lead: f.forecast_lead })}
                      </td>
                      {f.abstained ? (
                        <td className="p-2 text-text-muted" colSpan={4}>
                          {t('yieldx.abstain')}
                        </td>
                      ) : (
                        <>
                          <td className="p-2 text-right tabular-nums">
                            {n2(f.predicted_yield)} {unitLabel(f.unit)}
                          </td>
                          <td className="p-2 text-right tabular-nums">
                            {n2(f.interval_low)}–{n2(f.interval_high)}
                          </td>
                          <td className="p-2 text-right tabular-nums">{n2(f.normal_yield)}</td>
                          <td className={`p-2 text-right tabular-nums ${f.likely_shortfall ? 'font-bold text-red-700' : ''}`}>
                            {f.change_vs_normal === null ? '—' : `${Math.round(f.change_vs_normal * 100)}%`}
                          </td>
                        </>
                      )}
                      <td className="p-2">
                        {f.crop_tier}
                        {f.requires_human_review && <span className="block text-amber-800">{t('yieldx.needsReview')}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      )}
    </div>
  );
};

export default YieldOutlookPage;
