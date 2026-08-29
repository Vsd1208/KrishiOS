/**
 * Types for AI Evaluation, Observability & Trust Center.
 */

export type IndexKind = 'BASE' | 'CROP_SPECIFIC' | 'STATE_SPECIFIC' | 'SEASONAL' | string;
export type IndexStatus = 'BUILDING' | 'VALIDATING' | 'READY' | 'ACTIVE' | 'ARCHIVED' | 'FAILED' | 'ROLLED_BACK' | string;
export type BuildMode = 'BLUE_GREEN' | 'IN_PLACE' | 'DRY_RUN' | string;

export interface IndexVersion {
  id: number;
  version_number: number;
  collection_name: string;
  alias_name: string;
  index_kind: IndexKind;
  status: IndexStatus;
  build_mode: BuildMode;
  embedding_model: string;
  embedding_version: string;
  vector_size: number;
  chunk_count: number;
  document_count: number;
  validation_report?: Record<string, unknown> | null;
  promoted_at?: string | null;
  rolled_back_at?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IndexStatusSummary {
  alias_name: string;
  active_collection?: string | null;
  active_index?: IndexVersion | null;
  previous_index?: IndexVersion | null;
  indexes: IndexVersion[];
}
