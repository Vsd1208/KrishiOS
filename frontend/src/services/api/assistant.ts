/**
 * Phase 10c assistant: document analysis (runs in the background on the KrishiOS server).
 *
 * POST /api/v1/assistant/analyze-document      -> a job (202)
 * GET  /api/v1/assistant/analyze-document/{id} -> its status, with the result once done
 *
 * The document is read on the server and never stored; only the person who uploaded it can
 * read the result, which expires after an hour.
 */

import { apiClient } from '@/services/api/client';

export type AnalysisLanguage = 'en' | 'hi' | 'te';

export interface DocumentAnalysisResult {
  audience: 'officer' | 'farmer';
  language: string;
  text: string;
  text_en: string;
  pages: number;
  parts_read: number;
  parts_total: number;
  truncated: boolean;
  dropped_lines: number;
  translation_failed: boolean;
  model: string | null;
  /** Officer briefs: the rule-based extractor's fields (value, confidence, source spans). */
  extracted?: Record<string, unknown>;
}

export interface DocumentJob {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  queue_position: number;
  error?: string | null;
  result?: DocumentAnalysisResult | null;
}

export interface AnalyzeOptions {
  audience?: 'officer' | 'farmer';
  language?: AnalysisLanguage;
  crops?: string[];
  district?: string;
  state?: string;
}

export const asAnalysisLanguage = (lng: string | undefined): AnalysisLanguage => {
  const two = (lng ?? 'en').slice(0, 2);
  return two === 'hi' || two === 'te' ? two : 'en';
};

export const assistantApi = {
  analyzeDocument(file: File, opts: AnalyzeOptions = {}): Promise<DocumentJob> {
    const form = new FormData();
    form.append('file', file);
    form.append('audience', opts.audience ?? 'farmer');
    form.append('language', opts.language ?? 'en');
    if (opts.crops?.length) form.append('crops', opts.crops.join(','));
    if (opts.district) form.append('district', opts.district);
    if (opts.state) form.append('state', opts.state);
    return apiClient.postForm<DocumentJob>('/assistant/analyze-document', form);
  },

  getDocumentJob(jobId: string): Promise<DocumentJob> {
    return apiClient.get<DocumentJob>(`/assistant/analyze-document/${encodeURIComponent(jobId)}`);
  },
};
