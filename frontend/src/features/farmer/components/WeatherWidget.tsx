/**
 * WeatherWidget: current weather at the farmer's location and the spray-window advice from the
 * forecast. When the weather service has no reading it says so; it never shows default numbers.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Sun, CloudRain, Wind, Droplets, CheckCircle2, AlertTriangle, CloudOff } from 'lucide-react';

import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';
import type { WeatherObservation, WeatherForecast } from '@/types/weather';

interface WeatherWidgetProps {
  weather: WeatherObservation | null | undefined;
  forecast: WeatherForecast | null | undefined;
  isLoading?: boolean;
}

const ageSeconds = (iso?: string) => {
  if (!iso) return undefined;
  const ms = Date.now() - new Date(iso).getTime();
  return Number.isFinite(ms) && ms >= 0 ? Math.round(ms / 1000) : undefined;
};
const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : undefined);

export const WeatherWidget: React.FC<WeatherWidgetProps> = ({ weather, forecast, isLoading }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <Card variant="raised" padding="md">
        <div className="space-y-4">
          <Skeleton width="40%" height={20} />
          <Skeleton width="50%" height={36} />
          <div className="grid grid-cols-3 gap-2">
            <Skeleton height={40} />
            <Skeleton height={40} />
            <Skeleton height={40} />
          </div>
        </div>
      </Card>
    );
  }

  const temp = num(weather?.temperature_celsius);
  const humidity = num(weather?.relative_humidity_percent);
  const wind = num(weather?.wind_speed_mps);
  const rain = num(weather?.rainfall_mm);
  const spray = typeof forecast?.spray_window_favorable === 'boolean' ? forecast.spray_window_favorable : undefined;
  const age = ageSeconds(weather?.data_timestamp ?? weather?.fetched_at);

  return (
    <Card variant="raised" padding="md" className="space-y-4" data-testid="weather-widget">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-small font-semibold text-text">{t('weatherCard.title')}</span>
            {age !== undefined && <FreshnessIndicator freshnessSeconds={age} size="sm" />}
          </div>
          <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center" aria-hidden="true">
            {!weather ? <CloudOff className="w-5 h-5" /> : rain && rain > 0 ? <CloudRain className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-4">
        {!weather ? (
          <p className="text-small text-text-secondary" data-testid="no-weather-reading">
            {t('weatherCard.none')}
          </p>
        ) : (
          <>
            <div className="flex items-baseline justify-between gap-3">
              <div>
                <span className="text-display font-extrabold text-text tracking-tight">
                  {temp === undefined ? '—' : `${Math.round(temp)}°C`}
                </span>
                {weather.weather_condition && (
                  <p className="text-small font-medium text-text-secondary">{weather.weather_condition}</p>
                )}
              </div>
              {weather.district && (
                <span className="text-small font-semibold text-text text-right break-words">{weather.district}</span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
              {[
                { key: 'humidity', icon: <Droplets className="w-4 h-4 text-info-600 flex-shrink-0" aria-hidden="true" />, value: humidity === undefined ? '—' : `${Math.round(humidity)}%` },
                { key: 'wind', icon: <Wind className="w-4 h-4 text-teal-600 flex-shrink-0" aria-hidden="true" />, value: wind === undefined ? '—' : `${wind.toFixed(1)} m/s` },
                { key: 'rain', icon: <CloudRain className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />, value: rain === undefined ? '—' : `${rain.toFixed(1)} mm` },
              ].map((m) => (
                <div key={m.key} className="flex items-center gap-2 p-2 rounded-lg bg-surface-raised min-w-0">
                  {m.icon}
                  <div className="min-w-0">
                    <span className="text-[10px] uppercase text-text-muted block">{t(`canvas.weather.${m.key}`)}</span>
                    <span className="text-caption font-bold text-text">{m.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {spray !== undefined && (
          <div
            className={`p-3 rounded-lg border flex items-start gap-2.5 ${
              spray ? 'bg-success-50 border-success-200 text-success-900' : 'bg-warning-50 border-warning-200 text-warning-900'
            }`}
          >
            {spray ? (
              <CheckCircle2 className="w-4 h-4 text-success-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            )}
            <div className="space-y-0.5 text-caption">
              <strong className="font-semibold block">{spray ? t('weather.sprayOk') : t('weather.sprayNo')}</strong>
              {forecast?.spray_window_reason && <p className="leading-tight">{forecast.spray_window_reason}</p>}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default WeatherWidget;
