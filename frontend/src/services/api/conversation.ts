/**
 * Multilingual conversation API (Phase 3).
 *
 *   POST /conversation/turns         text turn (or a clarification choice)
 *   POST /conversation/voice-turns   recorded question -> transcript + same turn flow
 *   GET  /conversation/audio/{uuid}  synthesized reply audio (needs auth -> fetched as a blob)
 *   POST /feedback                   thumbs up/down on an answer
 */

import type { YieldForecast } from '@/services/api/forecasting';

import { config } from '@/app/config';
import { apiClient, getAccessToken } from '@/services/api/client';
import { ApiError } from '@/types/api';

export type BotLanguage = 'en' | 'hi' | 'te';

export interface ClarificationChoice {
  value: string | number;
  label: string;
}

export interface Clarification {
  slot: 'crop' | 'district' | string;
  question: string;
  choices: ClarificationChoice[];
}

export interface MediaCard {
  uuid: string;
  kind: string;
  title: string;
  url: string;
  source_org: string | null;
  licence: string | null;
  language: string | null;
  duration_s: number | null;
  verified: boolean;
}

export interface Citation {
  title?: string;
  source?: string;
  url?: string;
  [key: string]: unknown;
}

export interface TurnResult {
  conversation_id: string;
  turn_id: string;
  /** `retake`: photo turns only (blurry photo or no plant in it). */
  status: 'answered' | 'clarification' | 'smalltalk' | 'refused' | 'retake';
  language: BotLanguage;
  reply_text: string;
  reply_text_en: string | null;
  intent: string | null;
  detected_language: string | null;
  clarification: Clarification | null;
  citations: Citation[];
  slots: Record<string, unknown>;
  translation_status: string | null;
  requires_review: boolean;
  review_reason: string | null;
  providers: Record<string, unknown>;
  weather: Record<string, unknown> | null;
  audio_uuid: string | null;
  resumed_question: string | null;
  media: MediaCard[];
  /** Phase 8: structured yield forecast for yield questions (a model estimate). */
  yield_forecast?: YieldForecast | null;
  /** Phase 9: local photo findings (possibilities, never a diagnosis). */
  vision?: VisionCard | null;
  /** Active official bulletins for the district and crop (photo answers). */
  bulletins?: { uuid: string; title: string; authority: string; severity: string; valid_to: string | null }[];
  quality_issues?: string[];
  transcript?: string;
}

export interface VisionCard {
  crop: string | null;
  crop_confirmed_by_farmer: boolean;
  crop_candidates: [string, number][];
  candidate_conditions: { name: string; confidence: number }[];
  model_name: string;
  model_version: string;
  official: false;
}

export interface FarmerProfileHint {
  district_lgd_code?: number;
  crops?: string[];
}

export interface TurnRequest {
  text?: string;
  language: BotLanguage;
  conversation_id?: string | null;
  choice?: { slot: string; value: string | number } | null;
  speak?: boolean;
  profile?: FarmerProfileHint | null;
  /** Assisted mode: an extension worker asking for a consenting, assigned farmer. */
  act_as_farmer_id?: number | null;
  /** "Ask about this" on a Govt Connect bulletin (official text given to the bot). */
  bulletin_uuid?: string | null;
}

export type FeedbackReason =
  | 'wrong'
  | 'unclear'
  | 'not_applicable'
  | 'unsafe'
  | 'translation'
  | 'other';

/** First model load on CPU can take over a minute; voice adds STT + TTS. */
const TURN_TIMEOUT_MS = 120_000;

export const conversationApi = {
  sendTurn(body: TurnRequest): Promise<TurnResult> {
    return apiClient.post<TurnResult>('/conversation/turns', { text: '', ...body }, {
      timeout: TURN_TIMEOUT_MS,
    });
  },

  sendVoiceTurn(
    audio: Blob,
    language: BotLanguage,
    conversationId?: string | null,
    speak = true,
    actAsFarmerId?: number | null,
  ): Promise<TurnResult> {
    const form = new FormData();
    form.append('file', audio, 'question.webm');
    form.append('language', language);
    form.append('speak', String(speak));
    if (conversationId) form.append('conversation_id', conversationId);
    if (actAsFarmerId) form.append('act_as_farmer_id', String(actAsFarmerId));
    return apiClient.postForm<TurnResult>('/conversation/voice-turns', form, {
      timeout: TURN_TIMEOUT_MS,
    });
  },

  sendPhotoTurn(
    photo: Blob,
    language: BotLanguage,
    conversationId?: string | null,
    text = '',
    profile?: FarmerProfileHint | null,
  ): Promise<TurnResult> {
    const form = new FormData();
    form.append('file', photo, 'photo.jpg');
    form.append('language', language);
    if (text) form.append('text', text);
    if (conversationId) form.append('conversation_id', conversationId);
    if (profile?.district_lgd_code) form.append('district_lgd_code', String(profile.district_lgd_code));
    if (profile?.crops?.length) form.append('crops', profile.crops.join(','));
    return apiClient.postForm<TurnResult>('/conversation/photo-turns', form, {
      timeout: TURN_TIMEOUT_MS,
    });
  },

  async fetchAudio(audioUuid: string): Promise<Blob> {
    const token = getAccessToken();
    const response = await fetch(`${config.apiBaseUrl}/conversation/audio/${audioUuid}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new ApiError(response.status, 'audio_unavailable', 'Audio is not available.');
    }
    return response.blob();
  },

  sendFeedback(
    turnId: string,
    rating: 'up' | 'down',
    language: BotLanguage,
    reason?: FeedbackReason,
  ): Promise<unknown> {
    return apiClient.post('/feedback', {
      target_type: 'answer',
      target_id: turnId,
      rating,
      reason: reason ?? null,
      language,
    });
  },
};
