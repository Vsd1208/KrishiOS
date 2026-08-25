/**
 * TypeScript types for Agent Runtime execution matching backend schemas.
 *
 * See: backend/app/agents/api/schemas.py
 */

export interface AgentExecutionRequest {
  goal: string;
  session_id?: string;
  state?: string;
  district?: string;
  crop?: string;
  season?: string;
}

export interface AgentCitation {
  source?: string;
  title?: string;
  document_type?: string;
  relevance?: number;
  snippet?: string;
  page?: number | string;
  authority?: string;
}

export interface AgentResultItem {
  agent: string;
  status: 'completed' | 'failed' | 'running' | string;
  output: string;
  confidence: number;
  grounded: boolean;
  citations: AgentCitation[];
  error?: string | null;
}

export interface AgentExecutionResponse {
  goal: string;
  status: 'completed' | 'partial' | 'failed' | string;
  execution_id: string;
  results: AgentResultItem[];
  evaluation?: Record<string, unknown>;
}
