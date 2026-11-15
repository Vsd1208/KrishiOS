/**
 * Assisted mode (F6) and feedback triage (F13) APIs.
 *
 *   GET  /extension/farmers                 farmers assigned to me (with consent status)
 *   POST /extension/farmers/batch           register up to 50 farmers with consent
 *   POST /extension/farmers/{id}/consent    record / revoke consent
 *   GET  /extension/review-queue            assisted answers not yet shared
 *   POST /extension/turns/{uuid}/share      share with the farmer or discard
 *   GET  /feedback/summary | /feedback | /feedback/regression-cases, POST /feedback/{uuid}/triage
 */

import { apiClient } from '@/services/api/client';

export type ConsentMethod = 'verbal_recorded' | 'signed_form' | 'otp' | 'in_app';
export const CONSENT_METHODS: ConsentMethod[] = ['verbal_recorded', 'signed_form', 'otp', 'in_app'];

export interface AssignedFarmer {
  farmer_id: number;
  full_name: string;
  preferred_language: string;
  district_id: number;
  village: string;
  consent_status: 'pending' | 'granted' | 'revoked';
  consent_method: ConsentMethod | null;
}

export interface ConsentInput {
  granted: boolean;
  method: ConsentMethod;
  evidence?: string | null;
}

export interface NewFarmer {
  full_name: string;
  phone: string;
  preferred_language: 'en' | 'hi' | 'te';
  district_id: number;
  village: string;
  landholding_acres: number;
  consent: ConsentInput;
}

export interface BatchRow {
  phone: string;
  status: 'created' | 'duplicate_phone' | 'error';
  farmer_id: number | null;
  detail: string | null;
}

export interface QueuedAnswer {
  turn_uuid: string;
  farmer_id: number;
  language: string;
  question: string;
  answer: string;
  answer_en: string | null;
  requires_review: boolean;
  citations: { title?: string; source?: string }[];
  created_at: string;
}

export interface FeedbackBreakdownRow {
  value: string;
  count: number;
  down: number;
  down_rate: number;
}

export interface FeedbackSummary {
  total: number;
  breakdown: Record<string, FeedbackBreakdownRow[]>;
  down_reasons: Record<string, number>;
  pending_triage: number;
}

export interface FeedbackItem {
  uuid: string;
  target_type: string;
  target_id: string;
  rating: 'up' | 'down';
  reason: string | null;
  comment: string | null;
  language: string | null;
  status: 'new' | 'triaged' | 'converted_to_regression' | 'dismissed';
  created_at: string;
  question: string | null;
  answer: string | null;
  intent: string | null;
}

export type TriageStatus = 'triaged' | 'converted_to_regression' | 'dismissed';

export const extensionApi = {
  myFarmers: () => apiClient.get<AssignedFarmer[]>('/extension/farmers'),
  registerBatch: (farmers: NewFarmer[]) =>
    apiClient.post<BatchRow[]>('/extension/farmers/batch', { farmers }),
  recordConsent: (farmerId: number, consent: ConsentInput) =>
    apiClient.post<AssignedFarmer>(`/extension/farmers/${farmerId}/consent`, consent),
  reviewQueue: () => apiClient.get<QueuedAnswer[]>('/extension/review-queue'),
  share: (turnUuid: string, share: boolean) =>
    apiClient.post<{ turn_uuid: string; shared: boolean }>(`/extension/turns/${turnUuid}/share`, {
      share,
    }),
};

export const feedbackApi = {
  summary: () => apiClient.get<FeedbackSummary>('/feedback/summary'),
  list: (params: { rating?: 'up' | 'down'; status?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.rating) q.set('rating', params.rating);
    if (params.status) q.set('status_filter', params.status);
    const qs = q.toString();
    return apiClient.get<FeedbackItem[]>(`/feedback${qs ? `?${qs}` : ''}`);
  },
  triage: (uuid: string, status: TriageStatus) =>
    apiClient.post<{ uuid: string; status: string }>(`/feedback/${uuid}/triage`, { status }),
  regressionCases: () => apiClient.get<Record<string, unknown>[]>('/feedback/regression-cases'),
};
