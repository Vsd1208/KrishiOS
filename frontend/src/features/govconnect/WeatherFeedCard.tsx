/**
 * Dashboard weather feed (Phase 5). Official warnings come first and are styled as official;
 * the model forecast follows, with whether an independent source agrees, when it was fetched,
 * and where it came from. When the device is offline the last cached copy is shown and labelled.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, CloudRain, HelpCircle, Landmark, TriangleAlert } from 'lucide-react';

import { feedApi, type CrossCheck, type DistrictFeed } from '@/services/api/govconnect';
import { formatDate, SEVERITY_STYLE } from './format';

const CHECK_STYLE: Record<CrossCheck['status'], string> = {
  agree: 'bg-success-50 text-success-700',
  disagree: 'bg-amber-50 text-amber-800',
  unverified: 'bg-surface-raised text-text-secondary',
};

export const WeatherFeedCard: React.FC = () => {
  const { t } = useTranslation();
  const { data = [], isLoading } = useQuery({
    queryKey: ['govconnect', 'weather-feed'],
    queryFn: feedApi.weatherFeed,
    staleTime: 10 * 60 * 1000,
  });
  if (isLoading || data.length === 0) return null;
  return (
    <div className="space-y-3">
      {data.map((d) => (
        <DistrictWeather key={d.lgd_district_code} feed={d} />
      ))}
      <p className="text-caption text-text-muted">
        {t('weather.attribution', { list: data[0]?.attribution.join(' · ') ?? '' })}
      </p>
    </div>
  );
};

const DistrictWeather: React.FC<{ feed: DistrictFeed }> = ({ feed }) => {
  const { t, i18n } = useTranslation();
  const check = feed.crosscheck?.status ?? 'unverified';
  const CheckIcon =
    check === 'agree' ? CheckCircle2 : check === 'disagree' ? TriangleAlert : HelpCircle;
  return (
    <section
      aria-label={feed.district_name ?? undefined}
      className="rounded-2xl border border-border bg-surface p-4 space-y-3"
    >
      <h2 className="text-body font-bold text-text flex items-center gap-2">
        <CloudRain className="w-4 h-4 text-info-700" aria-hidden="true" />
        {t('weather.title', { district: feed.district_name ?? '—' })}
      </h2>

      {feed.official_warnings.map((w) => (
        <div key={w.uuid} className="rounded-xl border-2 border-info-200 bg-info-50/40 p-2.5 text-small">
          <span className="flex flex-wrap items-center gap-1.5 text-caption font-semibold text-info-700">
            <Landmark className="w-3.5 h-3.5" aria-hidden="true" />
            {t('govt.official')} · {w.authority}
            <span className={`px-2 py-0.5 rounded-full ${SEVERITY_STYLE[w.severity]}`}>
              {t(`govt.severity.${w.severity}`)}
            </span>
          </span>
          <span className="block pt-1 text-text">{w.title}</span>
          <span className="block text-caption text-text-muted">
            {t('govt.validUntil')} {formatDate(w.valid_to, i18n.language)}
          </span>
        </div>
      ))}

      {feed.forecast.length > 0 ? (
        <ul className="grid grid-cols-5 gap-1.5 text-center text-caption" aria-label={t('weather.forecast')}>
          {feed.forecast.slice(0, 5).map((day) => (
            <li key={day.date} className="rounded-lg bg-surface-raised p-1.5">
              <span className="block text-text-muted">
                {new Intl.DateTimeFormat(i18n.language, { weekday: 'short' }).format(new Date(day.date))}
              </span>
              <span className="block font-semibold text-text">{Math.round(day.temperature_max_celsius)}°</span>
              <span className="block text-info-700">{Math.round(day.precipitation_sum_mm)} mm</span>
              <span className="block text-text-muted">{Math.round(day.precipitation_probability_percent)}%</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-caption text-text-muted">{t('weather.noForecast')}</p>
      )}

      <div className="flex flex-wrap items-center gap-2 text-caption">
        <span
          className={`flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold ${CHECK_STYLE[check]}`}
          title={feed.crosscheck?.reasons.join('; ') || undefined}
        >
          <CheckIcon className="w-3.5 h-3.5" aria-hidden="true" />
          {t(`weather.check.${check}`)}
        </span>
        {feed.spray && (
          <span className={feed.spray.favorable ? 'text-success-700' : 'text-amber-800'}>
            {feed.spray.favorable ? t('weather.sprayOk') : t('weather.sprayNo')}
          </span>
        )}
        <span className={feed.stale ? 'text-danger-700' : 'text-text-muted'}>
          {feed.age_minutes === null
            ? t('weather.never')
            : t('weather.updated', { minutes: feed.age_minutes })}
        </span>
      </div>
      {check === 'disagree' && (
        <p className="text-caption text-amber-800">{feed.crosscheck?.reasons.join('; ')}</p>
      )}
      <p className="text-caption text-text-muted">{t('weather.modelNote')}</p>
    </section>
  );
};
