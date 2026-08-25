/**
 * TypeScript types for Multilingual Voice Intelligence matching backend schemas.
 *
 * See: backend/app/voice/schemas/voice.py
 */

export interface AudioRecordResponse {
  id: number;
  uuid: string;
  owner_uuid: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  duration_seconds: number;
  language_detected?: string | null;
  language_confidence?: number | null;
  created_at: string;
}

export interface TranscriptResponse {
  id: number;
  uuid: string;
  audio_uuid: string;
  raw_transcript: string;
  detected_language: string;
  language_confidence: number;
  transcription_confidence: number;
  model_name: string;
  model_version: string;
  normalized_query?: string | null;
  detected_intent?: string | null;
  extracted_entities?: Record<string, unknown>[] | null;
  created_at: string;
}

export interface VoiceQueryResponse {
  request_id: string;
  audio_id: number;
  audio_uuid: string;
  detected_language: string;
  raw_transcript: string;
  normalized_query: string;
  response_text: string;
  spoken_audio_reference?: string | null;
  citations: Array<{
    source_title?: string;
    authority?: string;
    document_type?: string;
    snippet?: string;
    [key: string]: unknown;
  }>;
  confidence: number;
  is_code_switched: boolean;
  processing_time_ms: number;
  agent_used: string;
}
