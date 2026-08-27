/**
 * Enterprise Semantic Retrieval API Service.
 *
 * Interacts with:
 * - POST /api/v1/retrieval/search
 */

import { apiClient } from '@/services/api/client';
import type { RetrievalSearchRequest, RetrievalSearchResponse } from '@/types/officer';

export const retrievalApi = {
  /** Run semantic search across ICAR and State agricultural document indexes. */
  async search(request: RetrievalSearchRequest): Promise<RetrievalSearchResponse> {
    return apiClient.post<RetrievalSearchResponse>('/retrieval/search', request);
  },
};
