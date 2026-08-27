/**
 * Human-in-the-Loop Officer Reviews API Service.
 *
 * Interacts with:
 * - GET /api/v1/proactive/reviews
 * - POST /api/v1/proactive/reviews/{alert_id}/action
 */

import { apiClient } from '@/services/api/client';
import type { AlertNotification } from '@/types/proactive';
import type { OfficerReviewActionRequest } from '@/types/officer';

export interface ReviewListParams {
  offset?: number;
  limit?: number;
}

export const reviewsApi = {
  /** List high-impact alerts awaiting agricultural officer sign-off. */
  async listPendingReviews(params: ReviewListParams = {}): Promise<AlertNotification[]> {
    const query = new URLSearchParams();
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    if (params.limit !== undefined) query.set('limit', String(params.limit));

    const qs = query.toString();
    return apiClient.get<AlertNotification[]>(`/proactive/reviews${qs ? `?${qs}` : ''}`);
  },

  /** Approve or reject a pending alert with optional notes or edited message. */
  async takeAction(
    alertId: number,
    actionPayload: OfficerReviewActionRequest,
  ): Promise<AlertNotification> {
    return apiClient.post<AlertNotification>(
      `/proactive/reviews/${alertId}/action`,
      actionPayload,
    );
  },
};
