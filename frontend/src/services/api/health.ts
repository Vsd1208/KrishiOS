/**
 * Health check API service.
 */

import { apiClient } from './client';

export interface HealthResponse {
  status: string;
}

export interface ReadinessResponse {
  status: string;
  database: string;
}

export async function healthCheck(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>('/health', { skipAuth: true });
}

export async function readinessCheck(): Promise<ReadinessResponse> {
  return apiClient.get<ReadinessResponse>('/ready', { skipAuth: true });
}
