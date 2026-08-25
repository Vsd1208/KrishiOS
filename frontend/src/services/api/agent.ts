/**
 * Agent Runtime API Service.
 *
 * Interacts with:
 * - POST /api/v1/agents/execute
 */

import { apiClient } from '@/services/api/client';
import type { AgentExecutionRequest, AgentExecutionResponse } from '@/types/agent';

export const agentApi = {
  /** Execute an agricultural agent goal/query. */
  async execute(request: AgentExecutionRequest): Promise<AgentExecutionResponse> {
    return apiClient.post<AgentExecutionResponse>('/agents/execute', request);
  },
};
