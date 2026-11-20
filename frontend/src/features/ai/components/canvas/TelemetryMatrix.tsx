/**
 * TelemetryMatrix: weather readings attached to this answer. Only readings the backend sent are
 * shown; a missing reading shows a dash, and there is no spray-window verdict unless the backend
 * gave one. Mandi prices live in the dashboard's AGMARKNET card, not here.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Thermometer, Droplets, Wind, CloudRain, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';

interface TelemetryMatrixProps {
  telemetry?: Record<string, unknown>;
  district?: string;
  crop?: string;
}

const read = (o: Record<string, unknown>, k: string) => (typeof o[k] === 'number' ? (o[k] as number) : undefined);

export const TelemetryMatrix: React.FC<TelemetryMatrixProps> = ({ telemetry = {}, district }) => {
  const { t } = useTranslation();
  const metrics = [
    {
      key: 'temp',
      label: t('canvas.weather.temp'),
      value: read(telemetry, 'temperature_celsius'),
      unit: '°C',
      icon: <Thermometer className="w-3.5 h-3.5 text-warning-600" aria-hidden="true" />,
    },
    {
      key: 'humidity',
      label: t('canvas.weather.humidity'),
      value: read(telemetry, 'relative_humidity_percent'),
      unit: '%',
      icon: <Droplets className="w-3.5 h-3.5 text-info-600" aria-hidden="true" />,
    },
    {
      key: 'wind',
      label: t('canvas.weather.wind'),
      value: read(telemetry, 'wind_speed_kmh'),
      unit: ' km/h',
      icon: <Wind className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />,
    },
    {
      key: 'rain',
      label: t('canvas.weather.rain'),
      value: read(telemetry, 'rainfall_mm'),
      unit: ' mm',
      icon: <CloudRain className="w-3.5 h-3.5 text-info-600" aria-hidden="true" />,
    },
  ];
  const anyReading = metrics.some((m) => m.value !== undefined);
  const spray =
    typeof telemetry.spray_window_favorable === 'boolean' ? (telemetry.spray_window_favorable as boolean) : undefined;
  const sprayReason =
    typeof telemetry.spray_window_reason === 'string' ? (telemetry.spray_window_reason as string) : undefined;

  return (
    <div className="space-y-4 animate-fadeIn">
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-info-100 text-info-700">
          <Activity className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-small font-bold text-text">{t('canvas.weather.title')}</h4>
          {district && <p className="text-caption text-text-muted">{t('canvas.weather.district', { district })}</p>}
        </div>
      </div>

      {!anyReading && spray === undefined ? (
        <div
          className="p-6 rounded-xl border border-dashed border-border bg-surface-raised text-center space-y-2"
          data-testid="no-weather"
        >
          <Activity className="w-8 h-8 text-text-muted mx-auto opacity-60" aria-hidden="true" />
          <p className="text-small text-text-secondary font-medium">{t('canvas.weather.none')}</p>
          <p className="text-caption text-text-muted max-w-sm mx-auto">{t('canvas.weather.noneHelp')}</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {metrics.map((m) => (
              <div key={m.key} className="p-3 rounded-xl bg-surface border border-border space-y-1">
                <div className="flex items-center justify-between text-caption text-text-muted">
                  <span>{m.label}</span>
                  {m.icon}
                </div>
                <p className="text-heading font-extrabold text-text tabular-nums">
                  {m.value === undefined ? '—' : `${m.value}${m.unit}`}
                </p>
              </div>
            ))}
          </div>
          {spray !== undefined && (
            <div
              className={`p-3.5 rounded-xl border flex items-start gap-3 ${
                spray ? 'bg-success-50 border-success-200 text-success-900' : 'bg-danger-50 border-danger-200 text-danger-900'
              }`}
            >
              {spray ? (
                <CheckCircle2 className="w-5 h-5 text-success-600 shrink-0 mt-0.5" aria-hidden="true" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-danger-600 shrink-0 mt-0.5" aria-hidden="true" />
              )}
              <div className="space-y-0.5">
                <span className="text-small font-bold">
                  {spray ? t('canvas.weather.sprayOk') : t('canvas.weather.sprayNo')}
                </span>
                {sprayReason && <p className="text-caption leading-relaxed">{sprayReason}</p>}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default TelemetryMatrix;
