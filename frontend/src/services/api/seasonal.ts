/**
 * Phase 10d district seasonal outlook (officers).
 *
 * GET /api/v1/seasonal/outlook?season=JJAS
 *
 * A research outlook alongside IMD's official forecasts. Variables without tested skill come
 * back with display "withhold" and no probabilities.
 */

import { apiClient } from '@/services/api/client';

export type OutlookSeason = 'JJAS' | 'OND' | 'JF' | 'MAM';
export type OutlookVariable = 'rain' | 'tmax' | 'tmin';

export interface OutlookProbabilities {
  p_below: number;
  p_near: number;
  p_above: number;
  lower_tercile: number;
  upper_tercile: number;
}

export interface OutlookDistrict {
  lgd_district_code: number;
  district: string;
  state: string | null;
  variables: Record<OutlookVariable, OutlookProbabilities | null>;
}

export interface OutlookVariableMeta {
  unit: string;
  test_rpss: number;
  display: 'show' | 'weak' | 'withhold';
}

export interface SeasonOutlook {
  version: string;
  season: OutlookSeason;
  season_name: string;
  issue_month: number;
  data_through: number;
  history: [number, number];
  method: string;
  variables: Record<OutlookVariable, OutlookVariableMeta>;
  districts: OutlookDistrict[];
}

export const seasonalApi = {
  getOutlook(season: OutlookSeason): Promise<SeasonOutlook> {
    return apiClient.get<SeasonOutlook>(`/seasonal/outlook?season=${season}`);
  },
};
