/**
 * Officer API Service.
 *
 * Interacts with:
 * - GET /api/v1/officers
 * - GET /api/v1/officers/{id}
 */

import { apiClient } from '@/services/api/client';
import type { Officer } from '@/types/domain';

export const officerApi = {
  /** List registered agricultural officers. */
  async listOfficers(offset: number = 0, limit: number = 100): Promise<Officer[]> {
    return apiClient.get<Officer[]>(`/officers?offset=${offset}&limit=${limit}`);
  },

  /** Get officer by ID. */
  async getOfficer(officerId: number): Promise<Officer> {
    return apiClient.get<Officer>(`/officers/${officerId}`);
  },
};
