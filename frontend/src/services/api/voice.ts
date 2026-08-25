/**
 * Multilingual Voice Intelligence API Service.
 *
 * Interacts with:
 * - POST /api/v1/voice/query (Multipart audio file upload)
 * - GET /api/v1/voice/audio/{uuid}
 * - GET /api/v1/voice/transcripts/{uuid}
 */

import { apiClient } from '@/services/api/client';
import type { VoiceQueryResponse, AudioRecordResponse, TranscriptResponse } from '@/types/voice';

export interface VoiceQueryOptions {
  hintLanguage?: string;
  analysisId?: number;
}

export const voiceApi = {
  /**
   * Submit an audio recording (WAV/MP3/M4A/WEBM) for speech recognition,
   * language detection, agent execution, and synthesized spoken advisory.
   */
  async submitVoiceQuery(
    audioBlob: Blob,
    filename: string = 'query.webm',
    options: VoiceQueryOptions = {},
  ): Promise<VoiceQueryResponse> {
    const formData = new FormData();
    formData.append('file', audioBlob, filename);
    if (options.hintLanguage) {
      formData.append('hint_language', options.hintLanguage);
    }
    if (options.analysisId !== undefined) {
      formData.append('analysis_id', String(options.analysisId));
    }

    return apiClient.postForm<VoiceQueryResponse>('/voice/query', formData);
  },

  /** Get audio record metadata by UUID. */
  async getAudioRecord(audioUuid: string): Promise<AudioRecordResponse> {
    return apiClient.get<AudioRecordResponse>(`/voice/audio/${audioUuid}`);
  },

  /** Get speech transcript by UUID. */
  async getTranscript(transcriptUuid: string): Promise<TranscriptResponse> {
    return apiClient.get<TranscriptResponse>(`/voice/transcripts/${transcriptUuid}`);
  },
};
