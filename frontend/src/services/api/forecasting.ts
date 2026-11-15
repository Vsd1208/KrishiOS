/** Yield Intelligence (Phase 8) and the F15 insurance helper. */

import { apiClient } from '@/services/api/client';

export type Season = 'Kharif' | 'Rabi' | 'Zaid' | 'Whole Year';

export interface YieldForecast {
  lgd_district_code: number;
  crop_canonical: string;
  crop_names?: { en: string; hi?: string; te?: string };
  season: Season;
  crop_year: number;
  crop_tier: 'A' | 'B' | 'C';
  forecast_lead: number;
  unit: string;
  model_name: string;
  model_version: string;
  generated_at: string;
  predicted_yield: number | null;
  interval_low: number | null;
  interval_high: number | null;
  normal_yield: number | null;
  change_vs_normal: number | null;
  available_modalities: string[];
  missing_modalities: string[];
  in_distribution: boolean;
  requires_human_review: boolean;
  abstained: boolean;
  abstain_reason: string | null;
  likely_shortfall?: boolean;
  official: false;
}

export interface DistrictRef {
  lgd_district_code: number;
  district_name: string;
  state_name: string;
}

export interface Outlook {
  district: DistrictRef;
  season: Season | null;
  items: YieldForecast[];
  counts: { forecasts: number; abstained: number; likely_shortfall: number; needs_review: number };
}

export interface ModelInfo {
  provider: string;
  provider_kind: string;
  latest_import: null | {
    model_name: string;
    model_version: string;
    rows: number;
    imported_at: string;
    generated_at: string;
    target?: string;
    validation?: Record<string, unknown>;
  };
}

export interface GuidanceItem {
  id: string;
  text: string;
  source: string;
  source_url: string;
  checked?: string;
  needs_official_source?: string | null;
}

export interface InsuranceHelper {
  scheme: { name: string; summary: string; benefits: string; source_url: string } | null;
  status: 'verified' | 'pending_officer_verification';
  guidance: GuidanceItem[];
  official_portal: string;
  yield_context: (YieldForecast & { notice: string }) | null;
}

const qs = (p: Record<string, string | number | null | undefined>) =>
  Object.entries(p)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&');

export const forecastingApi = {
  model: () => apiClient.get<ModelInfo>('/forecasting/model'),
  outlook: (lgd: number, season?: Season | null) =>
    apiClient.get<Outlook>(`/forecasting/outlook?${qs({ lgd_district_code: lgd, season })}`),
  forecast: (lgd: number, crop: string, season?: Season | null) =>
    apiClient.get<{ forecast: YieldForecast | null; status: string }>(
      `/forecasting/forecast?${qs({ lgd_district_code: lgd, crop, season })}`,
    ),
  runImport: () => apiClient.post<Record<string, unknown>>('/forecasting/import', {}),
  insurance: (p: { lgd?: number | null; crop?: string | null; season?: Season | null; language: string }) =>
    apiClient.get<InsuranceHelper>(
      `/schemes/insurance/helper?${qs({ lgd_district_code: p.lgd, crop: p.crop, season: p.season, language: p.language })}`,
    ),
};
