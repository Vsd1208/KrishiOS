import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { assistantApi } from '@/services/api/assistant';
import { DocumentBriefPage } from '../DocumentBriefPage';

vi.mock('@/services/api/assistant', async (orig) => ({
  ...(await orig<typeof import('@/services/api/assistant')>()),
  assistantApi: { analyzeDocument: vi.fn(), getDocumentJob: vi.fn() },
}));
const api = vi.mocked(assistantApi);

const done = {
  job_id: 'j1',
  status: 'done' as const,
  queue_position: 0,
  result: {
    audience: 'officer' as const, language: 'en', text: 'Document type: advisory\nActions: spray',
    text_en: 'Document type: advisory', pages: 14, parts_read: 5, parts_total: 7, truncated: true,
    dropped_lines: 1, translation_failed: false, model: 'qwen2.5:7b',
    extracted: { fields: { authority: { value: 'India Meteorological Department' },
      valid_to: { value: '2026-07-30T23:59:00+05:30' }, crops: { value: ['paddy', 'cotton'] } } },
  },
};

const submit = () => {
  const file = new File(['x'], 'advisory.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getByLabelText(/Document \(PDF/), { target: { files: [file] } });
  fireEvent.change(screen.getByLabelText(/Focus crops/), { target: { value: 'paddy, cotton' } });
  fireEvent.click(screen.getByRole('button', { name: /Make brief/ }));
};

describe('DocumentBriefPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('shows the brief, the extracted fields and what was removed', async () => {
    api.analyzeDocument.mockResolvedValue(done);
    render(<DocumentBriefPage />);
    submit();

    expect(await screen.findByText(/Actions: spray/)).toBeInTheDocument();
    expect(screen.getByText('India Meteorological Department')).toBeInTheDocument();
    expect(screen.getByText('2026-07-30')).toBeInTheDocument();
    expect(screen.getByText('paddy, cotton')).toBeInTheDocument();
    expect(screen.getByText(/1 line removed/)).toBeInTheDocument();
    expect(screen.getByText(/Read 5 of 7 sections/)).toBeInTheDocument();
    const opts = api.analyzeDocument.mock.calls[0]?.[1];
    expect(opts).toMatchObject({ audience: 'officer', language: 'en', crops: ['paddy', 'cotton'] });
  });

  it('says so when the job fails', async () => {
    api.analyzeDocument.mockResolvedValue({ job_id: 'j2', status: 'failed', queue_position: 0 });
    render(<DocumentBriefPage />);
    submit();
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not read the document/);
  });
});
