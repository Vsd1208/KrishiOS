/**
 * Knowledge Graph Candidates API Service.
 *
 * Interacts with:
 * - GET /api/v1/graph/candidates
 * - POST /api/v1/graph/candidates/{id}/review
 */

import { apiClient } from '@/services/api/client';
import type { GraphCandidate, ReviewCandidateRequest } from '@/types/officer';

export const graphApi = {
  /** List extracted graph knowledge candidates awaiting officer validation. */
  async listCandidates(status: string = 'PENDING'): Promise<GraphCandidate[]> {
    return apiClient.get<GraphCandidate[]>(`/graph/candidates?status=${status}`);
  },

  /** Approve or reject a candidate relationship. */
  async reviewCandidate(
    candidateId: number,
    payload: ReviewCandidateRequest,
  ): Promise<GraphCandidate> {
    return apiClient.post<GraphCandidate>(`/graph/candidates/${candidateId}/review`, payload);
  },
};
