/**
 * Provider transparency API (Sprint 11): which model / data source is active for each
 * capability, and whether it is live, a sandbox, or a mock.
 */

import { apiClient } from './client';

export type ProviderKind = 'live' | 'sandbox' | 'mock';

export interface ProviderStatus {
  capability: string;
  configured: string | null;
  name: string | null;
  version: string | null;
  kind: ProviderKind | null;
  sends_data_off_device: boolean | null;
  description: string | null;
  error: string | null;
}

export interface ProvidersResponse {
  providers: ProviderStatus[];
  policy_violations: string[];
}

export async function getProviders(): Promise<ProvidersResponse> {
  return apiClient.get<ProvidersResponse>('/providers', { skipAuth: true });
}
