/**
 * Govt–Farmer Connect (Phase 4), LGD catalog lookups and saved farmer locations (F2).
 *
 *   /govconnect/bulletins…      officer: upload/compose, edit, translate, approve, withdraw…
 *   /govconnect/inbox…          farmer: Govt Updates (read, ack, flag, listen)
 *   /govconnect/analytics|flags officer: delivery/read/ack/flags/questions
 *   /catalog/districts…         LGD district search and blocks
 *   /farmers/me/locations       F2 saved places
 */

import { apiClient } from '@/services/api/client';

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type BulletinStatus =
  | 'draft'
  | 'needs_review'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'withdrawn'
  | 'superseded'
  | 'expired';
export type Lang = 'en' | 'hi' | 'te';

export interface Span {
  start: number;
  end: number;
  text: string;
}

export interface BulletinTranslation {
  language: Lang;
  title: string;
  body: string;
  status: 'passthrough' | 'auto_approved' | 'pending_review' | 'blocked' | 'approved';
  provider: string | null;
  check_issues: string[];
  back_translation: string | null;
  approved_at: string | null;
}

export interface BulletinSummary {
  uuid: string;
  status: BulletinStatus;
  title: string;
  authority: string;
  authority_level: 'national' | 'state' | 'district' | 'block';
  severity: Severity;
  hazard_type: string | null;
  original_language: Lang;
  issued_at: string | null;
  valid_from: string | null;
  valid_to: string | null;
  district_codes: number[];
  block_codes: number[];
  crops: string[];
  source_type: 'upload' | 'composed' | 'feed';
  publish_at: string | null;
  published_at: string | null;
  index_state: string | null;
  created_at: string | null;
}

export interface BulletinDetail extends BulletinSummary {
  body: string;
  source_name: string | null;
  source_url: string | null;
  recommended_actions: string[];
  target_languages: Lang[];
  segment: { min_acres?: number; max_acres?: number };
  provenance: Record<string, Span[]>;
  extraction: {
    extractor?: string;
    low_confidence?: string[];
    ambiguous?: Record<string, unknown>;
    fields?: Record<string, { value: unknown; confidence: number }>;
  };
  translations: BulletinTranslation[];
  readiness: string[];
  supersedes: string | null;
  withdrawn_reason: string | null;
}

export type BulletinFields = Partial<
  Pick<
    BulletinDetail,
    | 'title'
    | 'authority'
    | 'authority_level'
    | 'source_name'
    | 'source_url'
    | 'issued_at'
    | 'valid_from'
    | 'valid_to'
    | 'hazard_type'
    | 'severity'
    | 'district_codes'
    | 'block_codes'
    | 'crops'
    | 'recommended_actions'
    | 'target_languages'
    | 'segment'
    | 'original_language'
    | 'body'
  >
>;

export interface AuditEntry {
  at: string;
  actor: string;
  action: string;
  detail: Record<string, unknown>;
}

export interface BulletinStats extends BulletinSummary {
  recipients: number;
  notified: number;
  suppressed: number;
  deduplicated: number;
  read: number;
  acknowledged: number;
  flagged: number;
  questions: number;
  read_rate: number | null;
  ack_rate: number | null;
  flag_rate: number | null;
}

export interface FlagItem {
  delivery_id: number;
  bulletin_uuid: string;
  title: string;
  farmer_id: number;
  language: string;
  match_level: string;
  reason: string | null;
  comment: string | null;
  flagged_at: string | null;
  status: string | null;
}

export interface InboxItem {
  bulletin_uuid: string;
  official: true;
  state: 'active' | 'expired' | 'withdrawn' | 'superseded';
  language: Lang;
  title: string;
  body: string;
  original_language: Lang;
  original_title: string;
  original_body: string;
  recommended_actions: string[];
  authority: string;
  authority_level: string;
  severity: Severity;
  hazard_type: string | null;
  issued_at: string | null;
  valid_from: string | null;
  valid_to: string | null;
  source_url: string | null;
  translated: boolean;
  withdrawn_reason: string | null;
  superseded_by: string | null;
  read_at: string | null;
  acknowledged_at: string | null;
  flag_reason: string | null;
}

export type FlagReason = 'not_applicable' | 'unclear' | 'wrong_location' | 'other';

export interface District {
  lgd_district_code: number;
  district_name: string;
  lgd_state_code: number;
  state_name: string;
}

export interface Block {
  lgd_block_code: number;
  block_name: string;
  lgd_district_code: number;
}

export interface FarmerLocation {
  id: number;
  label: string;
  lgd_district_code: number;
  lgd_block_code: number | null;
  village: string | null;
  is_primary: boolean;
  district_name: string;
  state_name: string;
  block_name: string | null;
}

export interface LocationInput {
  label: string;
  lgd_district_code: number;
  lgd_block_code?: number | null;
  village?: string | null;
  is_primary?: boolean;
}

const B = '/govconnect/bulletins';

export const govconnectApi = {
  list: (status?: string) =>
    apiClient.get<BulletinSummary[]>(`${B}${status ? `?status_filter=${status}` : ''}`),
  get: (uuid: string) => apiClient.get<BulletinDetail>(`${B}/${uuid}`),
  compose: (body: BulletinFields & { body: string }) => apiClient.post<BulletinDetail>(B, body),
  upload: (file: File, fields: BulletinFields = {}) => {
    const form = new FormData();
    form.append('file', file);
    form.append('fields', JSON.stringify(fields));
    return apiClient.postForm<BulletinDetail>(`${B}/upload`, form, { timeout: 120_000 });
  },
  edit: (uuid: string, fields: BulletinFields) =>
    apiClient.patch<BulletinDetail>(`${B}/${uuid}`, fields),
  translate: (uuid: string) =>
    apiClient.post<BulletinDetail>(`${B}/${uuid}/translate`, undefined, { timeout: 180_000 }),
  approveTranslation: (uuid: string, lang: Lang, edited: { title?: string; body?: string } = {}) =>
    apiClient.post<BulletinDetail>(`${B}/${uuid}/translations/${lang}/approve`, edited),
  approve: (uuid: string, publishAt?: string | null) =>
    apiClient.post<{ result: Record<string, unknown>; bulletin: BulletinDetail }>(
      `${B}/${uuid}/approve`,
      { publish_at: publishAt || null },
      { timeout: 120_000 },
    ),
  withdraw: (uuid: string, reason: string) =>
    apiClient.post<BulletinDetail>(`${B}/${uuid}/withdraw`, { reason }),
  supersede: (uuid: string) => apiClient.post<BulletinDetail>(`${B}/${uuid}/supersede`),
  audit: (uuid: string) => apiClient.get<AuditEntry[]>(`${B}/${uuid}/audit`),
  analytics: () => apiClient.get<BulletinStats[]>('/govconnect/analytics'),
  flags: (status = 'new') => apiClient.get<FlagItem[]>(`/govconnect/flags?status_filter=${status}`),
  triageFlag: (deliveryId: number, status: 'reviewed' | 'dismissed') =>
    apiClient.post(`/govconnect/flags/${deliveryId}/triage`, { status }),

  inbox: (activeOnly = false) =>
    apiClient.get<InboxItem[]>(`/govconnect/inbox${activeOnly ? '?active_only=true' : ''}`),
  markRead: (uuid: string) => apiClient.post(`/govconnect/inbox/${uuid}/read`),
  acknowledge: (uuid: string) => apiClient.post(`/govconnect/inbox/${uuid}/ack`),
  flag: (uuid: string, reason: FlagReason, comment?: string) =>
    apiClient.post(`/govconnect/inbox/${uuid}/flag`, { reason, comment: comment || null }),
  listen: (uuid: string) =>
    apiClient.post<{ audio_uuid: string; provider: string }>(
      `/govconnect/inbox/${uuid}/listen`,
      undefined,
      { timeout: 120_000 },
    ),
};

export const catalogApi = {
  searchDistricts: (prefix: string) =>
    apiClient.get<District[]>(
      `/catalog/districts?prefix=true&name=${encodeURIComponent(prefix)}`,
    ),
  district: (code: number) => apiClient.get<District>(`/catalog/districts/${code}`),
  blocks: (code: number) => apiClient.get<Block[]>(`/catalog/districts/${code}/blocks`),
};

export const locationsApi = {
  list: () => apiClient.get<FarmerLocation[]>('/farmers/me/locations'),
  add: (body: LocationInput) => apiClient.post<FarmerLocation>('/farmers/me/locations', body),
  update: (id: number, body: LocationInput) =>
    apiClient.put<FarmerLocation>(`/farmers/me/locations/${id}`, body),
  remove: (id: number) => apiClient.delete(`/farmers/me/locations/${id}`),
};

// ── Phase 5: district weather feed, feed health, web push ─────────────────────

export interface ForecastDay {
  date: string;
  temperature_min_celsius: number;
  temperature_max_celsius: number;
  precipitation_probability_percent: number;
  precipitation_sum_mm: number;
  max_wind_speed_mps: number;
  weather_condition: string;
}

export interface CrossCheck {
  status: 'agree' | 'disagree' | 'unverified';
  days_compared?: number;
  tmax_mae_c?: number | null;
  rain_total_primary_mm?: number | null;
  rain_total_reference_mm?: number | null;
  reasons: string[];
  primary?: string;
  reference?: string;
}

export interface DistrictFeed {
  lgd_district_code: number;
  district_name: string | null;
  state_name: string | null;
  official_warnings: BulletinSummary[];
  forecast: ForecastDay[];
  spray: { favorable: boolean; reason: string } | null;
  crosscheck: CrossCheck | null;
  providers: Record<string, string> | null;
  fetched_at: string | null;
  age_minutes: number | null;
  stale: boolean;
  attribution: string[];
}

export interface FeedsStatus {
  window_hours: number;
  weather_snapshots: Record<string, number>;
  weather_success_rate: number | null;
  weather_crosscheck: Record<string, number>;
  latest_weather_run: string | null;
  feed_bulletins: Record<string, number>;
}

export const feedApi = {
  weatherFeed: () => apiClient.get<DistrictFeed[]>('/govconnect/weather-feed'),
  status: (hours = 24) => apiClient.get<FeedsStatus>(`/govconnect/feeds/status?hours=${hours}`),
  pushConfig: () =>
    apiClient.get<{ public_key: string | null; enabled: boolean }>('/notifications/push/config'),
  subscribePush: (sub: PushSubscriptionJSON) =>
    apiClient.post('/notifications/push/subscriptions', sub),
  unsubscribePush: (endpoint: string) =>
    apiClient.post('/notifications/push/subscriptions/remove', { endpoint }),
};
