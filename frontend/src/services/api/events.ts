/**
 * Proactive Events API Service.
 *
 * Interacts with:
 * - POST /api/v1/proactive/events
 */

import { apiClient } from '@/services/api/client';
import type { EventIngestRequest, EventIngestResponse } from '@/types/officer';

export const eventsApi = {
  /** Ingest an external/regional agricultural event to trigger proactive decisions. */
  async ingestEvent(payload: EventIngestRequest): Promise<EventIngestResponse> {
    return apiClient.post<EventIngestResponse>('/proactive/events', payload);
  },
};
