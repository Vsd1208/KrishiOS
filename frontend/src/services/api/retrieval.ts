import { apiClient } from '@/services/api/client';
import type { RetrievalSearchRequest, RetrievalSearchResponse } from '@/types/officer';
import type { IndexVersion, IndexStatusSummary } from '@/types/evaluation';

export const retrievalApi = {
  /** Run semantic search across ICAR and State agricultural document indexes. */
  async search(request: RetrievalSearchRequest): Promise<RetrievalSearchResponse> {
    return apiClient.post<RetrievalSearchResponse>('/retrieval/search', request);
  },

  /** List all built and immutable retrieval index versions. */
  async listIndexes(): Promise<IndexVersion[]> {
    return apiClient.get<IndexVersion[]>('/indexes');
  },

  /** Get active live alias status and Blue/Green version deployment history. */
  async getIndexStatus(): Promise<IndexStatusSummary> {
    return apiClient.get<IndexStatusSummary>('/indexes/status');
  },
};
