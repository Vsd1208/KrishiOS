import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../client';
import { asAnalysisLanguage, assistantApi } from '../assistant';

describe('assistantApi', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('submits a farmer document with language and crop context', async () => {
    const post = vi.spyOn(apiClient, 'postForm').mockResolvedValue({ job_id: 'j1', status: 'queued', queue_position: 0 });
    const file = new File(['text'], 'advisory.pdf', { type: 'application/pdf' });
    const job = await assistantApi.analyzeDocument(file, { language: 'te', crops: ['paddy', 'cotton'] });

    expect(job.job_id).toBe('j1');
    const [path, form] = post.mock.calls[0] as [string, FormData];
    expect(path).toBe('/assistant/analyze-document');
    expect(form.get('audience')).toBe('farmer');
    expect(form.get('language')).toBe('te');
    expect(form.get('crops')).toBe('paddy,cotton');
    expect(form.get('district')).toBeNull();
  });

  it('polls a job by id', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ job_id: 'a b', status: 'done' });
    await assistantApi.getDocumentJob('a b');
    expect(get).toHaveBeenCalledWith('/assistant/analyze-document/a%20b');
  });

  it('maps app languages to the ones the server supports', () => {
    expect(asAnalysisLanguage('te')).toBe('te');
    expect(asAnalysisLanguage('hi-IN')).toBe('hi');
    expect(asAnalysisLanguage('mr')).toBe('en');
    expect(asAnalysisLanguage(undefined)).toBe('en');
  });
});
