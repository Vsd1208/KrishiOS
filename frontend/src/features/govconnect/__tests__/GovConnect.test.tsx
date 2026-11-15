import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import i18n from '@/i18n';
import { govconnectApi, type BulletinDetail, type InboxItem } from '@/services/api/govconnect';
import { schemesApi } from '@/services/api/grievance';
import { BulletinEditor } from '../BulletinEditor';
import { highlightSegments } from '../format';
import { GovtUpdatesPage } from '@/pages/farmer/GovtUpdatesPage';
import { GrievancePage } from '@/pages/farmer/GrievancePage';

vi.mock('@/services/api/govconnect', async (orig) => ({
  ...(await orig<typeof import('@/services/api/govconnect')>()),
  govconnectApi: {
    inbox: vi.fn(),
    acknowledge: vi.fn(),
    flag: vi.fn(),
    listen: vi.fn(),
    get: vi.fn(),
    edit: vi.fn(),
    translate: vi.fn(),
    approveTranslation: vi.fn(),
    approve: vi.fn(),
    withdraw: vi.fn(),
    supersede: vi.fn(),
    audit: vi.fn(),
  },
}));
vi.mock('@/services/api/grievance', async (orig) => ({
  ...(await orig<typeof import('@/services/api/grievance')>()),
  grievanceApi: { mine: vi.fn().mockResolvedValue([]), raise: vi.fn() },
  schemesApi: { list: vi.fn(), eligibility: vi.fn() },
}));

const gc = vi.mocked(govconnectApi);

function wrap(ui: React.ReactElement, path = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={ui} />
          <Route path="/farmer/ask" element={<p>chat page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const item: InboxItem = {
  bulletin_uuid: 'b1',
  official: true,
  state: 'active',
  language: 'te',
  title: 'భారీ వర్ష హెచ్చరిక',
  body: 'పిచికారీ వాయిదా వేయండి',
  original_language: 'en',
  original_title: 'Heavy rainfall warning',
  original_body: 'Postpone spraying.',
  recommended_actions: [],
  authority: 'Meteorological Centre Hyderabad (IMD)',
  authority_level: 'state',
  severity: 'HIGH',
  hazard_type: 'heavy_rain',
  issued_at: '2026-11-12T07:30:00Z',
  valid_from: null,
  valid_to: '2026-11-14T18:29:00Z',
  source_url: null,
  translated: true,
  withdrawn_reason: null,
  superseded_by: null,
  read_at: null,
  acknowledged_at: null,
  flag_reason: null,
};

describe('Govt Updates inbox', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('shows an official, translated bulletin with authority and validity', async () => {
    gc.inbox.mockResolvedValue([item]);
    wrap(<GovtUpdatesPage />);
    expect(await screen.findByText('భారీ వర్ష హెచ్చరిక')).toBeInTheDocument();
    expect(screen.getByText('Official')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText(/Issued by Meteorological Centre Hyderabad/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show the official original' }));
    expect(screen.getByText('Heavy rainfall warning')).toBeInTheDocument();
  });

  it('acknowledges, flags and opens "ask about this"', async () => {
    gc.inbox.mockResolvedValue([item]);
    gc.acknowledge.mockResolvedValue({});
    gc.flag.mockResolvedValue({});
    wrap(<GovtUpdatesPage />);
    fireEvent.click(await screen.findByRole('button', { name: /I have read this/ }));
    await waitFor(() => expect(gc.acknowledge).toHaveBeenCalledWith('b1'));
    fireEvent.click(screen.getByRole('button', { name: /Not for me/ }));
    fireEvent.click(screen.getByRole('button', { name: "Doesn't apply to me" }));
    await waitFor(() => expect(gc.flag).toHaveBeenCalledWith('b1', 'not_applicable'));
    fireEvent.click(screen.getByRole('button', { name: /Ask about this/ }));
    expect(await screen.findByText('chat page')).toBeInTheDocument();
  });
});

const detail: BulletinDetail = {
  uuid: 'b1',
  status: 'needs_review',
  title: 'Heavy rainfall warning',
  authority: 'Meteorological Centre (IMD)',
  authority_level: 'state',
  severity: 'HIGH',
  hazard_type: 'heavy_rain',
  original_language: 'en',
  issued_at: null,
  valid_from: null,
  valid_to: '2026-11-14T18:29:00Z',
  district_codes: [509],
  block_codes: [],
  crops: ['paddy'],
  source_type: 'upload',
  publish_at: null,
  published_at: null,
  index_state: null,
  created_at: null,
  body: 'Orange alert for Khammam district.',
  source_name: null,
  source_url: null,
  recommended_actions: [],
  target_languages: ['en', 'te'],
  segment: {},
  provenance: {
    severity: [{ start: 0, end: 12, text: 'Orange alert' }],
    district_codes: [{ start: 17, end: 24, text: 'Khammam' }],
  },
  extraction: { extractor: 'rules-v1', low_confidence: ['severity'] },
  translations: [
    {
      language: 'te',
      title: 'హెచ్చరిక',
      body: 'ఖమ్మం జిల్లాకు ఆరెంజ్ అలర్ట్.',
      status: 'pending_review',
      provider: 'indictrans2',
      check_issues: [],
      back_translation: 'Orange alert for Khammam district.',
      approved_at: null,
    },
  ],
  readiness: ['te: translation pending_review (needs officer approval)'],
  supersedes: null,
  withdrawn_reason: null,
};

describe('Bulletin editor', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('highlights provenance and blocks publishing until translations are approved', async () => {
    gc.get.mockResolvedValue(detail);
    gc.approveTranslation.mockResolvedValue({ ...detail, readiness: [] });
    wrap(<BulletinEditor uuid="b1" />);
    const mark = await screen.findByText('Khammam', { selector: 'mark' });
    expect(mark).toHaveAttribute('title', 'Target districts');
    expect(screen.getByText(/te: translation pending_review/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Approve and publish now/ })).toBeDisabled();
    expect(screen.getByText(/Back-translation/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Approve translation' }));
    await waitFor(() => expect(gc.approveTranslation).toHaveBeenCalledWith('b1', 'te', {}));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Approve and publish now/ })).toBeEnabled(),
    );
  });

  it('splits text into highlighted segments and skips stale spans', () => {
    const segs = highlightSegments('Orange alert for Khammam', {
      severity: [{ start: 0, end: 12, text: 'Orange alert' }],
      crops: [{ start: 17, end: 24, text: 'Warangal' }], // no longer matches the text
    });
    expect(segs).toEqual([
      { text: 'Orange alert', field: 'severity' },
      { text: ' for Khammam' },
    ]);
  });
});

describe('Scheme eligibility', () => {
  it('asks the verified questions and shows guidance with the official link', async () => {
    await i18n.changeLanguage('en');
    vi.mocked(schemesApi.list).mockResolvedValue([
      {
        key: 'pm_kisan',
        name: 'PM-KISAN',
        authority: 'MoA&FW',
        scope: 'central',
        summary: 'Income support',
        benefits: '',
        source_url: 'https://pmkisan.gov.in/',
        status_lookup_url: 'https://pmkisan.gov.in/',
        status: 'verified',
        verified_at: null,
        questions: [{ id: 'owns_cultivable_land', type: 'bool', question: 'Own land?' }],
      },
    ]);
    vi.mocked(schemesApi.eligibility).mockResolvedValue({
      status: 'likely_eligible',
      failed: [],
      missing: [],
      criteria: [],
      source_url: 'https://pmkisan.gov.in/',
      status_lookup_url: 'https://pmkisan.gov.in/',
      guidance_only: true,
    });
    wrap(<GrievancePage />);
    fireEvent.click(screen.getByRole('tab', { name: /Schemes/ }));
    fireEvent.click(await screen.findByRole('button', { name: /PM-KISAN/ }));
    fireEvent.click(screen.getByRole('radio', { name: 'Yes' }));
    fireEvent.click(screen.getByRole('button', { name: 'Check eligibility' }));
    await waitFor(() =>
      expect(schemesApi.eligibility).toHaveBeenCalledWith('pm_kisan', { owns_cultivable_land: true }, 'en'),
    );
    expect(await screen.findByText('You are likely eligible.')).toBeInTheDocument();
    expect(screen.getByText(/final decision/)).toBeInTheDocument();
  });
});
