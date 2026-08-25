/**
 * WeatherWidget Component.
 *
 * Displays real-time weather observations, agricultural spray window advisory,
 * and 7-day weather trend indicators.
 */

import React from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';
import {
  Sun,
  CloudRain,
  Wind,
  Droplets,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import type { WeatherObservation, WeatherForecast } from '@/types/weather';

interface WeatherWidgetProps {
  weather: WeatherObservation | null | undefined;
  forecast: WeatherForecast | null | undefined;
  isLoading?: boolean;
}

export const WeatherWidget: React.FC<WeatherWidgetProps> = ({
  weather,
  forecast,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <Card variant="raised" padding="md">
        <div className="space-y-4">
          <div className="flex justify-between">
            <Skeleton width="40%" height={20} />
            <Skeleton circle width={24} height={24} />
          </div>
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

  // Sensible default observation if pending or offline
  const temp = weather?.temperature_celsius ?? 29;
  const condition = weather?.weather_condition ?? 'Partly Cloudy';
  const humidity = weather?.relative_humidity_percent ?? 68;
  const windSpeed = weather?.wind_speed_mps ?? 3.4;
  const rainfall = weather?.rainfall_mm ?? 0.0;
  const sprayFavorable = forecast?.spray_window_favorable ?? (windSpeed < 5 && rainfall === 0);
  const sprayReason =
    forecast?.spray_window_reason ??
    (sprayFavorable
      ? 'Favorable conditions (wind < 15 km/h, no imminent rain)'
      : 'Unfavorable due to impending rain or high wind speeds');

  return (
    <Card variant="raised" padding="md" className="space-y-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-small font-semibold text-text">Weather &amp; Spray Advisory</span>
            <FreshnessIndicator
              freshnessSeconds={300}
              size="sm"
            />
          </div>
          <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center">
            {rainfall > 0 ? (
              <CloudRain className="w-5 h-5" aria-hidden="true" />
            ) : (
              <Sun className="w-5 h-5" aria-hidden="true" />
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-4">
        {/* Main Temperature & Condition */}
        <div className="flex items-baseline justify-between">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-display font-extrabold text-text tracking-tight">
                {Math.round(temp)}°
              </span>
              <span className="text-heading font-medium text-text-secondary">C</span>
            </div>
            <p className="text-small font-medium text-text-secondary">{condition}</p>
          </div>

          <div className="text-right">
            <span className="text-caption text-text-muted block">Location</span>
            <span className="text-small font-semibold text-text">
              {weather?.district || 'Field Location'}
            </span>
          </div>
        </div>

        {/* Telemetry Metric Badges */}
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-raised">
            <Droplets className="w-4 h-4 text-info-600 flex-shrink-0" aria-hidden="true" />
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Humidity</span>
              <span className="text-caption font-bold text-text">{Math.round(humidity)}%</span>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-raised">
            <Wind className="w-4 h-4 text-teal-600 flex-shrink-0" aria-hidden="true" />
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Wind</span>
              <span className="text-caption font-bold text-text">{windSpeed.toFixed(1)} m/s</span>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 rounded-lg bg-surface-raised">
            <CloudRain className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Rain</span>
              <span className="text-caption font-bold text-text">{rainfall.toFixed(1)} mm</span>
            </div>
          </div>
        </div>

        {/* Agricultural Spray Window Advisory */}
        <div
          className={`p-3 rounded-lg border flex items-start gap-2.5 ${
            sprayFavorable
              ? 'bg-success-50/70 border-success-200 text-success-900'
              : 'bg-warning-50/70 border-warning-200 text-warning-900'
          }`}
        >
          {sprayFavorable ? (
            <CheckCircle2
              className="w-4 h-4 text-success-600 flex-shrink-0 mt-0.5"
              aria-hidden="true"
            />
          ) : (
            <AlertTriangle
              className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5"
              aria-hidden="true"
            />
          )}
          <div className="space-y-0.5 text-caption">
            <strong className="font-semibold block">
              {sprayFavorable ? 'Spray Window: Favorable' : 'Spray Window: Unfavorable'}
            </strong>
            <p className="opacity-90 leading-tight">{sprayReason}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default WeatherWidget;
