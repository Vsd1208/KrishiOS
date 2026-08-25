/**
 * Agricultural Advisories API Service.
 *
 * Interacts with:
 * - GET /api/v1/live/advisories
 */

import { apiClient } from '@/services/api/client';
import type { AgriculturalAdvisory } from '@/types/advisory';

export interface AdvisoryParams {
  crop: string;
  state?: string;
  district?: string;
  force_refresh?: boolean;
}

export const advisoryApi = {
  /** Get ICAR and State Agricultural Department agromet advisories. */
  async getAdvisories(params: AdvisoryParams): Promise<AgriculturalAdvisory[]> {
    const query = new URLSearchParams();
    query.set('crop', params.crop);
    if (params.state) query.set('state', params.state);
    if (params.district) query.set('district', params.district);
    if (params.force_refresh) query.set('force_refresh', 'true');

    return apiClient.get<AgriculturalAdvisory[]>(`/live/advisories?${query.toString()}`);
  },
};
