/** F8 outbreak surveillance (Phase 9): crowd photo diagnoses per district and week. */

import { apiClient } from '@/services/api/client';

export interface HeatCell {
  lgd_district_code: number;
  district_name: string | null;
  state_name: string | null;
  crop: string;
  crop_name: string;
  condition: string;
  week_start: string;
  reporters: number;
  mean_confidence: number;
}

export interface OutbreakItem extends Omit<HeatCell, 'mean_confidence'> {
  baseline: number;
}

export const surveillanceApi = {
  heatmap: (weeks = 8, crop?: string) =>
    apiClient.get<{ weeks: number; cells: HeatCell[]; note: string }>(
      `/surveillance/heatmap?weeks=${weeks}${crop ? `&crop=${encodeURIComponent(crop)}` : ''}`,
    ),
  outbreaks: () => apiClient.get<{ week_start: string; items: OutbreakItem[] }>('/surveillance/outbreaks'),
};
