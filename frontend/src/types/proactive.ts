/**
 * Proactive intelligence types matching the backend Sprint 10 schemas.
 *
 * See: backend/app/proactive/api/schemas.py
 *      backend/app/models/proactive.py
 */

// ── Enums ────────────────────────────────────────────────────────────────────

export type RiskSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type AlertStatus =
  | 'CREATED'
  | 'EVALUATING'
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'SENT'
  | 'ACKNOWLEDGED'
  | 'EXPIRED'
  | 'CANCELLED';

export type NotificationChannel = 'SMS' | 'PUSH' | 'IN_APP' | 'VOICE';

export type AlertPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';

/** Freshness classification for time-sensitive data. */
export type FreshnessLevel = 'FRESH' | 'RECENT' | 'STALE' | 'EXPIRED' | 'UNKNOWN';

/** Confidence level derived from a numeric score. */
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

// ── Proactive Decision ───────────────────────────────────────────────────────

export interface ProactiveDecision {
  decision_id: string;
  event_id: string;
  farmer_id: number | null;
  field_id: number | null;
  risk_type: string;
  risk_severity: RiskSeverity;
  confidence: number;
  evidence_package: EvidencePackage;
  advisory_text: string;
  requires_review: boolean;
  valid_until: string | null;
  created_at: string;
}

// ── Evidence Package ─────────────────────────────────────────────────────────

export interface EvidencePackage {
  live_telemetry?: Record<string, unknown>;
  citations?: Citation[];
  graph_paths?: GraphPath[];
  vision_findings?: Record<string, unknown>[];
  active_rules?: string[];
  freshness_seconds?: number;
  confidence_breakdown?: Record<string, number>;
}

// ── Citation ─────────────────────────────────────────────────────────────────

export interface Citation {
  citation_id?: string;
  source_title: string;
  authority?: string;
  document_type?: string;
  page?: number | string;
  date?: string;
  relevance_score?: number;
  snippet?: string;
}

// ── Graph Path ───────────────────────────────────────────────────────────────

export interface GraphPath {
  path: string;
  relationship?: string;
  confidence?: number;
}

// ── Alert Notification ───────────────────────────────────────────────────────

export interface AlertNotification {
  id: number;
  uuid: string;
  decision_id: number | null;
  farmer_id: number;
  channel: NotificationChannel;
  title: string;
  message: string;
  priority: AlertPriority;
  status: AlertStatus;
  reviewed_by: string | null;
  review_note: string | null;
  sent_at: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

// ── Notification Preference ──────────────────────────────────────────────────

export interface NotificationPreference {
  id: number;
  farmer_id: number;
  preferred_channel: NotificationChannel;
  preferred_language: string;
  min_severity: RiskSeverity;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  enable_weather_alerts: boolean;
  enable_disease_alerts: boolean;
  enable_market_alerts: boolean;
  enable_scheme_alerts: boolean;
  created_at: string;
  updated_at: string;
}
