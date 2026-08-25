/**
 * TypeScript types for Vision Intelligence matching backend schemas.
 *
 * See: backend/app/vision/schemas/vision.py
 */

export type ImageAnalysisStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'QUALITY_FAILED'
  | 'COMPLETED'
  | 'FAILED';

export type ReviewStatus =
  | 'AUTO_APPROVED'
  | 'NEEDS_OFFICER_REVIEW'
  | 'APPROVED_BY_OFFICER'
  | 'REJECTED_BY_OFFICER';

export interface ImageUploadRequest {
  crop_hint?: string | null;
  field_uuid?: string | null;
}

export interface ImageUploadResponse {
  image_id: number;
  uuid: string;
  status: ImageAnalysisStatus;
}

export interface ObservationSchema {
  finding: string;
  confidence: number;
  bbox?: [number, number, number, number] | null;
}

export interface CandidateConditionSchema {
  name: string;
  confidence: number;
}

export interface AnalysisResponse {
  id: number;
  uuid: string;
  image_uuid: string;
  model_name: string;
  model_version: string;
  status: ImageAnalysisStatus;
  quality_score?: number | null;
  quality_issues?: string[] | null;
  crop_detected?: string | null;
  observations: ObservationSchema[];
  candidate_conditions: CandidateConditionSchema[];
  confidence_score?: number | null;
  review_status: ReviewStatus;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface AnalysisListResponse {
  total: number;
  offset: number;
  limit: number;
  items: AnalysisResponse[];
}
