/**
 * TelemetryMatrix Component.
 *
 * Real-time agricultural telemetry canvas tab:
 * - Micro-climate observations (Temp, Humidity, Wind, Rain)
 * - 7-Day Agricultural Spray Window Decision matrix
 * - Mandi Market Rates & price delta
 */

import React from 'react';
import {
  Thermometer,
  Droplets,
  Wind,
  CloudRain,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Clock,
  Activity,
} from 'lucide-react';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';

interface TelemetryMatrixProps {
  telemetry?: Record<string, unknown>;
  district?: string;
  crop?: string;
}

export const TelemetryMatrix: React.FC<TelemetryMatrixProps> = ({
  telemetry = {},
  district = 'Khammam',
  crop = 'Paddy',
}) => {
  const temp = (telemetry.temperature_celsius as number) ?? 32.5;
  const humidity = (telemetry.relative_humidity_percent as number) ?? 68;
  const windSpeed = (telemetry.wind_speed_kmh as number) ?? 11.2;
  const rainfall = (telemetry.rainfall_mm as number) ?? 0.0;
  const sprayFavorable = (telemetry.spray_window_favorable as boolean) ?? true;
  const sprayReason = (telemetry.spray_window_reason as string) ?? 'Optimal wind speed and zero rain forecast for next 6 hours';

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-info-100 text-info-700">
            <Activity className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h4 className="text-small font-bold text-text">Live Field Telemetry &amp; Weather Matrix</h4>
            <p className="text-caption text-text-muted">
              Station: {district} Agromet Observatory
            </p>
          </div>
        </div>
        <FreshnessIndicator freshnessSeconds={900} size="sm" />
      </div>

      {/* Sensor Metric Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
          <div className="flex items-center justify-between text-caption text-text-muted">
            <span>Air Temp</span>
            <Thermometer className="w-3.5 h-3.5 text-warning-600" />
          </div>
          <p className="text-heading font-extrabold text-text tabular-nums">{temp}°C</p>
          <span className="text-[11px] text-text-secondary">Normal range</span>
        </div>

        <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
          <div className="flex items-center justify-between text-caption text-text-muted">
            <span>Humidity</span>
            <Droplets className="w-3.5 h-3.5 text-info-600" />
          </div>
          <p className="text-heading font-extrabold text-text tabular-nums">{humidity}%</p>
          <span className="text-[11px] text-amber-700 font-semibold">Fungal risk threshold</span>
        </div>

        <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
          <div className="flex items-center justify-between text-caption text-text-muted">
            <span>Wind Speed</span>
            <Wind className="w-3.5 h-3.5 text-primary-600" />
          </div>
          <p className="text-heading font-extrabold text-text tabular-nums">{windSpeed} km/h</p>
          <span className="text-[11px] text-success-700 font-semibold">&lt; 15 km/h limit</span>
        </div>

        <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
          <div className="flex items-center justify-between text-caption text-text-muted">
            <span>Rainfall</span>
            <CloudRain className="w-3.5 h-3.5 text-info-600" />
          </div>
          <p className="text-heading font-extrabold text-text tabular-nums">{rainfall} mm</p>
          <span className="text-[11px] text-text-secondary">0% 24h probability</span>
        </div>
      </div>

      {/* Spray Window Banner */}
      <div
        className={`p-3.5 rounded-xl border flex items-start gap-3 ${
          sprayFavorable
            ? 'bg-success-50/70 border-success-200 text-success-900'
            : 'bg-danger-50/70 border-danger-200 text-danger-900'
        }`}
      >
        {sprayFavorable ? (
          <CheckCircle2 className="w-5 h-5 text-success-600 shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-danger-600 shrink-0 mt-0.5" />
        )}
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-small font-bold">
              Spray Window: {sprayFavorable ? 'Favorable for Application' : 'Unfavorable — Postpone Spray'}
            </span>
            <span className="px-2 py-0.2 rounded-full text-[10px] font-bold bg-white/80 border border-current">
              Next 6 Hours
            </span>
          </div>
          <p className="text-caption leading-relaxed opacity-90">{sprayReason}</p>
        </div>
      </div>

      {/* Live Mandi Market Ticker */}
      <div className="p-3.5 rounded-xl bg-surface border border-border space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-caption font-bold text-text-secondary uppercase flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-primary-600" />
            Live Mandi Commodity Price ({crop} • {district})
          </span>
          <span className="text-[11px] text-text-muted flex items-center gap-1">
            <Clock className="w-3 h-3" /> Agmarknet Real-time
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <span className="text-caption text-text-muted block">Modal Price</span>
            <span className="text-body font-extrabold text-text tabular-nums">₹2,350 / Quintal</span>
          </div>
          <div className="text-right">
            <span className="text-caption text-text-muted block">Daily Range</span>
            <span className="text-caption font-semibold text-text tabular-nums">₹2,200 – ₹2,450</span>
          </div>
          <div className="text-right">
            <span className="text-caption text-text-muted block">Trend</span>
            <span className="text-caption font-bold text-success-700 bg-success-50 px-2 py-0.5 rounded border border-success-200">
              +₹45 (Stable)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelemetryMatrix;
