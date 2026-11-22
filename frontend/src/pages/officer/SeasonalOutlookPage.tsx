/**
 * Seasonal outlook (/officer/seasonal): chance of below / near / above normal rainfall and
 * temperature per district for the coming season (Phase 10d). A research outlook alongside
 * IMD's official forecasts; officers review it before anything is shared with farmers.
 */

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Info } from 'lucide-react';

import {
  seasonalApi,
  type OutlookProbabilities,
  type OutlookSeason,
  type OutlookVariable,
} from '@/services/api/seasonal';

const SEASONS: OutlookSeason[] = ['JJAS', 'OND', 'JF', 'MAM'];
const VARIABLES: OutlookVariable[] = ['rain', 'tmax', 'tmin'];
const pct = (p: number) => `${Math.round(p * 100)}%`;

const TercileBar: React.FC<{ p: OutlookProbabilities; unit: string }> = ({ p, unit }) => {
  const { t } = useTranslation();
  const title = t('seasonal.limits', {
    low: p.lower_tercile,
    high: p.upper_tercile,
    unit,
  });
  return (
    <div title={title} aria-label={`${t('seasonal.below')} ${pct(p.p_below)}, ${t('seasonal.near')} ${pct(p.p_near)}, ${t('seasonal.above')} ${pct(p.p_above)}. ${title}`}>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full" aria-hidden="true">
        <span className="bg-info-400" style={{ width: pct(p.p_below) }} />
        <span className="bg-gray-300" style={{ width: pct(p.p_near) }} />
        <span className="bg-danger-400" style={{ width: pct(p.p_above) }} />
      </div>
      <div className="mt-0.5 flex justify-between text-[11px] text-text-muted">
        <span>{pct(p.p_below)}</span>
        <span>{pct(p.p_near)}</span>
        <span>{pct(p.p_above)}</span>
      </div>
    </div>
  );
};

export const SeasonalOutlookPage: React.FC = () => {
  const { t } = useTranslation();
  const [season, setSeason] = useState<OutlookSeason>('JJAS');
  const [state, setState] = useState('');
  const { data, isLoading, isError } = useQuery({
    queryKey: ['seasonal', 'outlook', season],
    queryFn: () => seasonalApi.getOutlook(season),
    staleTime: 60 * 60 * 1000,
  });

  const states = useMemo(
    () => [...new Set((data?.districts ?? []).map((d) => d.state).filter(Boolean) as string[])].sort(),
    [data],
  );
  const rows = (data?.districts ?? []).filter((d) => !state || d.state === state);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-heading font-bold text-text">{t('seasonal.title')}</h1>
        <p className="text-small text-text-secondary">{t('seasonal.subtitle')}</p>
      </div>

      <div className="flex items-start gap-2 p-3 rounded-xl bg-info-50 border border-info-200 text-caption text-info-900">
        <Info className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
        <p>{t('seasonal.disclaimer', { through: data?.data_through ?? '—' })}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" className="flex gap-1">
          {SEASONS.map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={season === s}
              onClick={() => setSeason(s)}
              className={`px-3 py-1.5 rounded-lg text-small font-semibold border cursor-pointer ${
                season === s ? 'bg-primary-600 text-white border-primary-600' : 'border-border text-text'
              }`}
            >
              {t(`seasonal.season.${s}`)}
            </button>
          ))}
        </div>
        <label htmlFor="seasonal-state" className="sr-only">{t('seasonal.state')}</label>
        <select
          id="seasonal-state"
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-surface border border-border text-small text-text"
        >
          <option value="">{t('seasonal.allStates')}</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-small text-text-muted">{t('common.loading')}</p>}
      {isError && <p role="alert" className="text-small text-danger-700">{t('seasonal.failed')}</p>}

      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {VARIABLES.map((v) => {
              const meta = data.variables[v];
              return (
                <div key={v} className="p-3 rounded-xl border border-border bg-surface text-caption">
                  <span className="font-semibold text-text block">{t(`seasonal.var.${v}`)}</span>
                  <span className={meta.display === 'withhold' ? 'text-danger-700' : meta.display === 'weak' ? 'text-warning-700' : 'text-success-700'}>
                    {t(`seasonal.display.${meta.display}`)}
                  </span>
                  <span className="text-text-muted block">{t('seasonal.skill', { rpss: meta.test_rpss.toFixed(2) })}</span>
                </div>
              );
            })}
          </div>

          <p className="text-caption text-text-muted">
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-info-400 mr-1" aria-hidden="true" />{t('seasonal.below')}
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-gray-300 mx-1 ml-3" aria-hidden="true" />{t('seasonal.near')}
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-danger-400 mx-1 ml-3" aria-hidden="true" />{t('seasonal.above')}
          </p>

          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full text-small">
              <thead>
                <tr className="text-left text-caption text-text-muted border-b border-border">
                  <th className="p-2 font-semibold">{t('seasonal.district')}</th>
                  {VARIABLES.map((v) => (
                    <th key={v} className="p-2 font-semibold min-w-[9rem]">{t(`seasonal.var.${v}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.lgd_district_code} className="border-b border-border last:border-0">
                    <td className="p-2">
                      <span className="font-medium text-text block">{d.district}</span>
                      <span className="text-caption text-text-muted">{d.state}</span>
                    </td>
                    {VARIABLES.map((v) => {
                      const p = d.variables[v];
                      return (
                        <td key={v} className="p-2 align-top">
                          {p ? (
                            <TercileBar p={p} unit={data.variables[v].unit === 'mm' ? 'mm' : '°C'} />
                          ) : (
                            <span className="text-caption text-text-muted">{t('seasonal.noSignal')}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-caption text-text-muted">{t('seasonal.method', { method: data.method, from: data.history[0], to: data.history[1] })}</p>
        </>
      )}
    </div>
  );
};

export default SeasonalOutlookPage;
