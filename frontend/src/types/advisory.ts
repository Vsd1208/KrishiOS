/**
 * TypeScript types for Agricultural Advisories matching backend live_data schemas.
 *
 * See: backend/app/live_data/schemas/advisory.py
 */

export type AdvisoryStatus = 'ACTIVE' | 'EXPIRED' | 'SUPERSEDED' | 'WITHDRAWN';

export interface AgriculturalAdvisory {
  advisory_id: string;
  title: string;
  content: string;
  crop: string;
  state: string;
  district?: string | null;
  issuing_authority: string;
  effective_from: string;
  effective_until: string;
  status: AdvisoryStatus;
  superseded_by_id?: string | null;
  recommended_practices: string[];
  warning_notes: string[];
  source_dataset?: string;
  fetched_at?: string;
}
