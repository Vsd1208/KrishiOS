/**
 * TypeScript types for Agricultural Officer Console & Reviews.
 *
 * See: backend/app/schemas/officer.py
 *      backend/app/proactive/api/schemas.py
 *      backend/app/graph/api/schemas.py
 *      backend/app/retrieval/api/schemas.py
 */

export interface OfficerReviewActionRequest {
  action: 'APPROVE' | 'REJECT';
  review_note?: string;
  edited_message?: string;
}

export interface EventIngestRequest {
  event_type: string;
  payload: Record<string, unknown>;
  source?: string;
  correlation_id?: string;
}

export interface EventIngestResponse {
  event_id: string;
  status: string;
  decisions_count: number;
  message: string;
}

export interface GraphCandidate {
  id: number;
  document_uuid: string;
  chunk_id: string;
  subject_label: string;
  subject_name: string;
  predicate: string;
  object_label: string;
  object_name: string;
  confidence: number;
  review_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  neo4j_rel_id?: string | null;
}

export interface ReviewCandidateRequest {
  action: 'APPROVE' | 'REJECT';
  note?: string;
}

export interface RetrievalSearchFilters {
  crop?: string;
  state?: string;
  district?: string;
  season?: string;
  language?: string;
  authority?: string;
  document_type?: string;
}

export interface RetrievalSearchRequest {
  query: string;
  filters?: RetrievalSearchFilters;
  top_k?: number;
  score_threshold?: number;
  include_delta?: boolean;
}

export interface CitationResponse {
  document_id?: number | null;
  title?: string | null;
  source?: string | null;
  source_url?: string | null;
  page_number?: number | null;
  chunk_id: string;
}

export interface RetrievalResultResponse {
  answer_context: string;
  chunk: string;
  similarity: number;
  ranking_score: number;
  freshness_score: number;
  authority_score: number;
  document: Record<string, unknown>;
  page?: number | null;
  chunk_id: string;
  collection: string;
  version?: string | null;
  metadata: Record<string, unknown>;
  citation: CitationResponse;
}

export interface RetrievalSearchResponse {
  query: string;
  total_results: number;
  latency_ms: number;
  results: RetrievalResultResponse[];
}
