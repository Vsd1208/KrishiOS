/**
 * Translation and NLU API services (Sprint 11).
 *
 * - POST /translation/translate (protected spans + number/unit checks + approval policy)
 * - POST /translation/check
 * - GET  /translation/glossary
 * - POST /translation/records/{uuid}/approve (officers)
 * - POST /nlu/parse
 */

import { apiClient } from './client';

export type AppLanguage = 'en' | 'hi' | 'te';
export type TranslationStatus = 'passthrough' | 'auto_approved' | 'pending_review' | 'blocked';

export interface TranslationChecks {
  passed: boolean;
  missing_numbers: string[];
  extra_numbers: string[];
  missing_units: string[];
  extra_units: string[];
  missing_protected_terms: string[];
  leftover_placeholders: string[];
  numbers_in_source: number;
}

export interface TranslateRequest {
  text: string;
  source_language: AppLanguage;
  target_language: AppLanguage;
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  personal_data?: boolean;
  back_translate?: boolean;
  persist?: boolean;
}

export interface TranslateResponse {
  source_language: AppLanguage;
  target_language: AppLanguage;
  text: string;
  status: TranslationStatus;
  deliverable: boolean;
  checks: TranslationChecks;
  provider: string | null;
  provider_version: string | null;
  glossary_version: string;
  cached: boolean;
  protected_spans: number;
  attempts: { provider: string; provider_version: string | null; outcome: string; detail: string; latency_ms: number | null }[];
  back_translation: string | null;
  record_uuid: string | null;
}

export interface NLUParse {
  intent: string;
  confidence: number;
  language: AppLanguage;
  is_code_switched: boolean;
  romanized: boolean;
  secondary_intents: string[];
  provider: string;
  provider_version: string;
  entities: {
    crop: string | null;
    crop_status: 'resolved' | 'ambiguous' | 'multiple' | 'not_found';
    crop_candidates: string[];
    district_lgd_code: number | null;
    district_name: string | null;
    district_candidates: number[];
    season: string | null;
    symptoms: string[];
    time_expression: string | null;
    scheme: string | null;
  };
}

export const translationApi = {
  translate: (req: TranslateRequest) =>
    apiClient.post<TranslateResponse>('/translation/translate', req),
  check: (source: string, translation: string) =>
    apiClient.post<TranslationChecks>('/translation/check', { source, translation }),
  approve: (recordUuid: string, editedText?: string) =>
    apiClient.post(`/translation/records/${recordUuid}/approve`, { edited_text: editedText ?? null }),
};

export const nluApi = {
  parse: (text: string, languageHint?: AppLanguage) =>
    apiClient.post<NLUParse>('/nlu/parse', { text, language_hint: languageHint ?? null }),
};
