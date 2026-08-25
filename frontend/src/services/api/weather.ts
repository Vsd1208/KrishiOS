/**
 * Live Weather Intelligence API Service.
 *
 * Interacts with:
 * - GET /api/v1/live/weather/current
 * - GET /api/v1/live/weather/forecast
 * - GET /api/v1/live/weather/alerts
 */

import { apiClient } from '@/services/api/client';
import type { WeatherObservation, WeatherForecast, WeatherAlert } from '@/types/weather';

export interface WeatherParams {
  latitude?: number;
  longitude?: number;
  district?: string;
  state?: string;
  field_id?: number;
  force_refresh?: boolean;
}

export interface ForecastParams extends WeatherParams {
  days?: number;
}

export const weatherApi = {
  /** Get current weather observation for a location/field. */
  async getCurrentWeather(params: WeatherParams = {}): Promise<WeatherObservation> {
    const query = new URLSearchParams();
    if (params.latitude !== undefined) query.set('latitude', String(params.latitude));
    if (params.longitude !== undefined) query.set('longitude', String(params.longitude));
    if (params.district) query.set('district', params.district);
    if (params.state) query.set('state', params.state);
    if (params.field_id !== undefined) query.set('field_id', String(params.field_id));
    if (params.force_refresh) query.set('force_refresh', 'true');

    const qs = query.toString();
    return apiClient.get<WeatherObservation>(`/live/weather/current${qs ? `?${qs}` : ''}`);
  },

  /** Get multi-day weather forecast with agricultural spray window. */
  async getForecast(params: ForecastParams = {}): Promise<WeatherForecast> {
    const query = new URLSearchParams();
    if (params.latitude !== undefined) query.set('latitude', String(params.latitude));
    if (params.longitude !== undefined) query.set('longitude', String(params.longitude));
    if (params.district) query.set('district', params.district);
    if (params.state) query.set('state', params.state);
    if (params.field_id !== undefined) query.set('field_id', String(params.field_id));
    if (params.days !== undefined) query.set('days', String(params.days));
    if (params.force_refresh) query.set('force_refresh', 'true');

    const qs = query.toString();
    return apiClient.get<WeatherForecast>(`/live/weather/forecast${qs ? `?${qs}` : ''}`);
  },

  /** Get active weather alerts and meteorological warnings. */
  async getAlerts(params: { latitude?: number; longitude?: number } = {}): Promise<WeatherAlert[]> {
    const query = new URLSearchParams();
    if (params.latitude !== undefined) query.set('latitude', String(params.latitude));
    if (params.longitude !== undefined) query.set('longitude', String(params.longitude));

    const qs = query.toString();
    return apiClient.get<WeatherAlert[]>(`/live/weather/alerts${qs ? `?${qs}` : ''}`);
  },
};
