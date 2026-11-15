/** Grievance tickets and the scheme catalog with eligibility Q&A (F4). */

import { apiClient } from '@/services/api/client';
import type { Lang } from '@/services/api/govconnect';

export type GrievanceCategory =
  | 'payment'
  | 'insurance_claim'
  | 'scheme_enrollment'
  | 'input_quality'
  | 'advisory'
  | 'infrastructure'
  | 'other';
export const GRIEVANCE_CATEGORIES: GrievanceCategory[] = [
  'payment',
  'insurance_claim',
  'scheme_enrollment',
  'input_quality',
  'advisory',
  'infrastructure',
  'other',
];
export type TicketStatus =
  | 'open'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'rejected'
  | 'reopened'
  | 'closed';

export interface TicketEvent {
  at: string;
  status: TicketStatus | null;
  note: string | null;
  public: boolean;
  by: 'farmer' | 'officer';
}

export interface Ticket {
  uuid: string;
  category: GrievanceCategory;
  subject: string;
  description: string;
  language: Lang;
  status: TicketStatus;
  priority: string;
  scheme_key: string | null;
  lgd_district_code: number | null;
  created_at: string;
  resolved_at: string | null;
  sla_due_at: string;
  breached: boolean;
  hours_left: number | null;
  events?: TicketEvent[];
  farmer_id?: number;
  assigned_to?: string | null;
}

export interface TicketInput {
  category: GrievanceCategory;
  subject: string;
  description: string;
  language: Lang;
  scheme_key?: string | null;
}

export interface SchemeQuestion {
  id: string;
  type: 'bool' | 'number' | 'choice';
  question: string | Record<string, string>;
  options?: string[] | null;
}

export interface Scheme {
  key: string;
  name: string | Record<string, string>;
  authority: string;
  scope: 'central' | 'state';
  summary: string | Record<string, string>;
  benefits: string | Record<string, string>;
  source_url: string;
  status_lookup_url: string | null;
  status: 'draft' | 'verified';
  verified_at: string | null;
  questions: SchemeQuestion[];
  criteria?: Record<string, unknown>[];
}

export interface EligibilityResult {
  status: 'likely_eligible' | 'not_eligible' | 'incomplete';
  failed: string[];
  missing: string[];
  criteria: { id: string; question: string; answered: boolean; met?: boolean; source?: string }[];
  source_url: string;
  status_lookup_url: string | null;
  guidance_only: true;
}

export const grievanceApi = {
  raise: (body: TicketInput) => apiClient.post<Ticket>('/grievances', body),
  mine: () => apiClient.get<Ticket[]>('/grievances/mine'),
  myTicket: (uuid: string) => apiClient.get<Ticket>(`/grievances/mine/${uuid}`),
  farmerAction: (uuid: string, action: 'close' | 'reopen', note?: string) =>
    apiClient.post<Ticket>(`/grievances/mine/${uuid}`, { action, note: note || null }),
  queue: (params: { status?: string; breachedOnly?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set('status_filter', params.status);
    if (params.breachedOnly) q.set('breached_only', 'true');
    const qs = q.toString();
    return apiClient.get<Ticket[]>(`/grievances/queue${qs ? `?${qs}` : ''}`);
  },
  queueTicket: (uuid: string) => apiClient.get<Ticket>(`/grievances/queue/${uuid}`),
  officerAction: (
    uuid: string,
    body: { status: TicketStatus; note?: string; public?: boolean },
  ) => apiClient.post<Ticket>(`/grievances/queue/${uuid}`, body),
};

export const schemesApi = {
  list: (language: Lang = 'en') => apiClient.get<Scheme[]>(`/schemes?language=${language}`),
  get: (key: string, language: Lang = 'en') =>
    apiClient.get<Scheme>(`/schemes/${key}?language=${language}`),
  eligibility: (key: string, answers: Record<string, unknown>, language: Lang) =>
    apiClient.post<EligibilityResult>(`/schemes/${key}/eligibility`, { answers, language }),
  importDrafts: () => apiClient.post<{ created: string[] }>('/schemes/import-drafts'),
  verify: (key: string) => apiClient.post<Scheme>(`/schemes/${key}/verify`),
};
