/**
 * TypeScript types for Weather Intelligence matching backend live_data schemas.
 *
 * See: backend/app/live_data/schemas/weather.py
 */

export interface WeatherObservation {
  latitude: number;
  longitude: number;
  district?: string | null;
  state?: string | null;
  temperature_celsius: number;
  apparent_temperature_celsius?: number | null;
  relative_humidity_percent: number;
  rainfall_mm: number;
  wind_speed_mps: number;
  wind_direction_degrees?: number | null;
  surface_pressure_hpa?: number | null;
  weather_code: number;
  weather_condition: string;
  cloud_cover_percent?: number | null;
  uv_index?: number | null;
  source_dataset?: string;
  fetched_at?: string;
  data_timestamp?: string;
  freshness_level?: 'FRESH' | 'RECENT' | 'STALE' | 'EXPIRED' | 'UNKNOWN';
}

export interface DailyForecastItem {
  date: string;
  temperature_min_celsius: number;
  temperature_max_celsius: number;
  precipitation_probability_percent: number;
  precipitation_sum_mm: number;
  max_wind_speed_mps: number;
  weather_condition: string;
}

export interface WeatherForecast {
  latitude: number;
  longitude: number;
  district?: string | null;
  state?: string | null;
  forecast_days: DailyForecastItem[];
  summary: string;
  spray_window_favorable: boolean;
  spray_window_reason: string;
  source_dataset?: string;
  fetched_at?: string;
  freshness_level?: 'FRESH' | 'RECENT' | 'STALE' | 'EXPIRED' | 'UNKNOWN';
}

export interface WeatherAlert {
  alert_id: string;
  headline: string;
  severity: 'Advisory' | 'Watch' | 'Warning' | 'Emergency' | string;
  event_type: 'Heatwave' | 'Heavy Rainfall' | 'Thunderstorm' | 'Frost' | string;
  affected_regions: string[];
  effective_from: string;
  effective_until: string;
  instruction: string;
  source_dataset?: string;
  fetched_at?: string;
}
