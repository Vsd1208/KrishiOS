/**
 * The likely range as a bar: the band is the interval, the dot the forecast and the tick the
 * normal yield, all on one scale so a reader sees at a glance whether normal sits inside the range.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';

const n2 = (v: number) => v.toFixed(2);

export const YieldRangeBar: React.FC<{
  low: number;
  high: number;
  forecast: number;
  normal: number;
  shortfall?: boolean;
  legend?: boolean;
}> = ({ low, high, forecast, normal, shortfall, legend = true }) => {
  const { t } = useTranslation();
  const lo = Math.min(low, normal);
  const hi = Math.max(high, normal);
  const pad = (hi - lo) * 0.08 || Math.max(Math.abs(hi), 1) * 0.05;
  const min = lo - pad;
  const span = hi + pad - min;
  const pct = (v: number) => `${((v - min) / span) * 100}%`;
  const label = t('yieldx.rangeBar', { forecast: n2(forecast), low: n2(low), high: n2(high), normal: n2(normal) });

  return (
    <div className="space-y-0.5" data-testid="yield-range-bar">
      <div role="img" aria-label={label} className="relative h-3 w-full rounded-full bg-border">
        <div
          className={`absolute inset-y-0 rounded-full ${shortfall ? 'bg-red-200' : 'bg-primary-200'}`}
          style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }}
        />
        <div
          className="absolute -top-0.5 -bottom-0.5 w-0.5 bg-text-secondary"
          style={{ left: pct(normal) }}
          aria-hidden="true"
        />
        <div
          className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface ${
            shortfall ? 'bg-red-700' : 'bg-primary-700'
          }`}
          style={{ left: pct(forecast) }}
          aria-hidden="true"
        />
      </div>
      {legend && (
        <p className="flex gap-3 text-caption text-text-muted" aria-hidden="true">
          <span className="flex items-center gap-1">
            <span className={`inline-block h-2 w-2 rounded-full ${shortfall ? 'bg-red-700' : 'bg-primary-700'}`} />
            {t('yieldx.legendForecast')}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-0.5 bg-text-secondary" />
            {t('yieldx.legendNormal')}
          </span>
        </p>
      )}
    </div>
  );
};

export default YieldRangeBar;
