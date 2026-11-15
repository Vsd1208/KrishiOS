import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import i18n from '@/i18n';
import { extensionApi, feedbackApi } from '@/services/api/extension';
import { ExtensionPage } from '../ExtensionPage';
import { parseFarmerLines } from '@/features/extension/parseFarmerLines';
import { FeedbackDashboardPage } from '../FeedbackDashboardPage';

vi.mock('@/services/api/extension', async (orig) => ({
  ...(await orig<typeof import('@/services/api/extension')>()),
  extensionApi: {
    myFarmers: vi.fn(),
    registerBatch: vi.fn(),
    recordConsent: vi.fn(),
    reviewQueue: vi.fn(),
    share: vi.fn(),
  },
  feedbackApi: { summary: vi.fn(), list: vi.fn(), triage: vi.fn(), regressionCases: vi.fn() },
}));
vi.mock('@/features/conversation/FarmerChat', () => ({
  FarmerChat: (p: { actAsFarmerId?: number; initialLanguage?: string }) => (
    <div>chat for {p.actAsFarmerId} in {p.initialLanguage}</div>
  ),
}));

const ext = vi.mocked(extensionApi);
const fb = vi.mocked(feedbackApi);

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const farmer = (over = {}) => ({
  farmer_id: 7,
  full_name: 'Lakshmi',
  preferred_language: 'te',
  district_id: 509,
  village: 'Kothagudem',
  consent_status: 'pending' as const,
  consent_method: null,
  ...over,
});

describe('parseFarmerLines', () => {
  const consent = { granted: true, method: 'signed_form' as const, evidence: 'F-12' };
  it('parses valid rows and reports bad line numbers', () => {
    const { farmers, errors } = parseFarmerLines(
      'Lakshmi, 9876543210, te, 509, Kothagudem, 2.5\n\nRamu, 12, te, 509, X, 1\nSita, 9876543211, fr, 509, Y, 1',
      consent,
    );
    expect(farmers).toHaveLength(1);
    expect(farmers[0]).toMatchObject({ phone: '9876543210', district_id: 509, landholding_acres: 2.5, consent });
    expect(errors).toEqual([3, 4]);
  });
});

describe('ExtensionPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('requires consent before asking on a farmer’s behalf', async () => {
    ext.myFarmers.mockResolvedValue([farmer()]);
    ext.recordConsent.mockResolvedValue(farmer({ consent_status: 'granted' }));
    wrap(<ExtensionPage />);
    expect(await screen.findByText('Consent pending')).toBeInTheDocument();
    expect(screen.queryByText('Ask on their behalf')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Record consent/ }));
    await waitFor(() =>
      expect(ext.recordConsent).toHaveBeenCalledWith(7, {
        granted: true,
        method: 'verbal_recorded',
        evidence: null,
      }),
    );
  });

  it('opens assisted chat in the farmer’s language', async () => {
    ext.myFarmers.mockResolvedValue([farmer({ consent_status: 'granted' })]);
    wrap(<ExtensionPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Ask on their behalf/ }));
    expect(screen.getByText('chat for 7 in te')).toBeInTheDocument();
    expect(screen.getByText(/Asking on behalf of Lakshmi/)).toBeInTheDocument();
  });

  it('cannot share an answer that still needs officer review', async () => {
    ext.myFarmers.mockResolvedValue([]);
    ext.reviewQueue.mockResolvedValue([
      {
        turn_uuid: 'u1',
        farmer_id: 7,
        language: 'te',
        question: 'q',
        answer: 'a',
        answer_en: 'a-en',
        requires_review: true,
        citations: [],
        created_at: '2026-11-13T00:00:00Z',
      },
    ]);
    wrap(<ExtensionPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Review before sharing' }));
    expect(await screen.findByRole('button', { name: /Share with farmer/ })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: /Discard/ }));
    await waitFor(() => expect(ext.share).toHaveBeenCalledWith('u1', false));
  });
});

describe('FeedbackDashboardPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('shows rates and triages a flagged answer into the regression suite', async () => {
    fb.summary.mockResolvedValue({
      total: 4,
      pending_triage: 1,
      down_reasons: { wrong: 1 },
      breakdown: {
        all: [{ value: 'all', count: 4, down: 1, down_rate: 0.25 }],
        language: [{ value: 'te', count: 4, down: 1, down_rate: 0.25 }],
        intent: [{ value: 'disease', count: 4, down: 1, down_rate: 0.25 }],
      },
    });
    fb.list.mockResolvedValue([
      {
        uuid: 'f1',
        target_type: 'answer',
        target_id: 't1',
        rating: 'down',
        reason: 'wrong',
        comment: null,
        language: 'te',
        status: 'new',
        created_at: '2026-11-13T00:00:00Z',
        question: 'blast?',
        answer: 'spray x',
        intent: 'disease',
      },
    ]);
    fb.triage.mockResolvedValue({ uuid: 'f1', status: 'converted_to_regression' });
    wrap(<FeedbackDashboardPage />);
    expect(await screen.findAllByText('25%')).not.toHaveLength(0);
    fireEvent.click(await screen.findByRole('button', { name: 'Add to regression suite' }));
    await waitFor(() => expect(fb.triage).toHaveBeenCalledWith('f1', 'converted_to_regression'));
  });
});
