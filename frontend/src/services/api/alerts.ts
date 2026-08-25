/**
 * Proactive Alerts and Notifications API Service.
 *
 * Interacts with:
 * - GET /api/v1/proactive/alerts
 * - POST /api/v1/proactive/alerts/{id}/acknowledge
 * - GET /api/v1/proactive/decisions
 * - GET /api/v1/proactive/preferences
 * - PUT /api/v1/proactive/preferences
 */

import { apiClient } from '@/services/api/client';
import type {
  AlertNotification,
  AlertStatus,
  NotificationPreference,
  ProactiveDecision,
} from '@/types/proactive';

export interface AlertListParams {
  farmer_id?: number;
  status_filter?: AlertStatus;
  limit?: number;
  offset?: number;
}

export const alertsApi = {
  /** List alerts for the current farmer or query by filter. */
  async listAlerts(params: AlertListParams = {}): Promise<AlertNotification[]> {
    const query = new URLSearchParams();
    if (params.farmer_id !== undefined) query.set('farmer_id', String(params.farmer_id));
    if (params.status_filter) query.set('status_filter', params.status_filter);
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));

    const qs = query.toString();
    return apiClient.get<AlertNotification[]>(`/proactive/alerts${qs ? `?${qs}` : ''}`);
  },

  /** Acknowledge an alert notification by ID. */
  async acknowledgeAlert(alertId: number): Promise<AlertNotification> {
    return apiClient.post<AlertNotification>(`/proactive/alerts/${alertId}/acknowledge`);
  },

  /** Query past proactive decisions & evidence packages. */
  async listDecisions(farmerId?: number): Promise<ProactiveDecision[]> {
    const query = farmerId ? `?farmer_id=${farmerId}` : '';
    return apiClient.get<ProactiveDecision[]>(`/proactive/decisions${query}`);
  },

  /** Get notification preferences for farmer. */
  async getPreferences(farmerId?: number): Promise<NotificationPreference> {
    const query = farmerId ? `?farmer_id=${farmerId}` : '';
    return apiClient.get<NotificationPreference>(`/proactive/preferences${query}`);
  },

  /** Update notification preferences. */
  async updatePreferences(
    prefs: Partial<NotificationPreference>,
    farmerId?: number,
  ): Promise<NotificationPreference> {
    const query = farmerId ? `?farmer_id=${farmerId}` : '';
    return apiClient.put<NotificationPreference>(`/proactive/preferences${query}`, prefs);
  },
};
