import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import i18n from '@/i18n';
import { forecastingApi, type YieldForecast } from '@/services/api/forecasting';
import { YieldCard } from '../YieldCard';
import { InsurancePage } from '@/pages/farmer/InsurancePage';

vi.mock('@/services/api/forecasting', async (orig) => ({
  ...(await orig<typeof import('@/services/api/forecasting')>()),
  forecastingApi: { model: vi.fn(), outlook: vi.fn(), forecast: vi.fn(), runImport: vi.fn(), insurance: vi.fn() },
}));

const base: YieldForecast = {
  lgd_district_code: 509, crop_canonical: 'paddy', crop_names: { en: 'Paddy (Rice)', te: 'వరి' },
  season: 'Rabi', crop_year: 2026, crop_tier: 'A', forecast_lead: 30, unit: 'Tonnes/Hectare',
  model_name: 'b3-lgbm-multicrop', model_version: 'v1', generated_at: '2026-11-15T00:00:00Z',
  predicted_yield: 2.8, interval_low: 2.3, interval_high: 3.3, normal_yield: 3.5, change_vs_normal: -0.2,
  available_modalities: ['weather', 'yield_history'], missing_modalities: [], in_distribution: true,
  requires_human_review: false, abstained: false, abstain_reason: null, likely_shortfall: false, official: false,
};

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

describe('YieldCard', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
  });

  it('shows the estimate, range, normal and the not-official notice', () => {
    wrap(<YieldCard forecast={base} />);
    expect(screen.getByText(/2\.80/)).toBeInTheDocument();
    expect(screen.getByText(/Likely range 2\.30–3\.30/)).toBeInTheDocument();
    expect(screen.getByText('20% below normal')).toBeInTheDocument();
    expect(screen.getByText(/not an official crop-cutting, YES-TECH or insurance figure/)).toBeInTheDocument();
  });

  it('shows no number for an abstention', () => {
    wrap(
      <YieldCard
        forecast={{ ...base, crop_tier: 'C', abstained: true, predicted_yield: null, interval_low: null,
          interval_high: null, normal_yield: null, change_vs_normal: null }}
        compact
      />,
    );
    expect(screen.getByText(/Not enough data/)).toBeInTheDocument();
    expect(screen.getByTestId('yield-card').textContent).not.toMatch(/\d\.\d\d/);
  });

  it('flags tier B forecasts for officer review, in Telugu too', async () => {
    await i18n.changeLanguage('te');
    wrap(<YieldCard forecast={{ ...base, crop_tier: 'B', requires_human_review: true }} />);
    expect(screen.getByText(/వరి/)).toBeInTheDocument();
    expect(screen.getByText(/అధికారి ఈ అంచనాను/)).toBeInTheDocument();
  });
});

describe('InsurancePage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
  });

  it('says guidance is pending verification and still links the official portal', async () => {
    vi.mocked(forecastingApi.insurance).mockResolvedValue({
      scheme: null, status: 'pending_officer_verification', guidance: [],
      official_portal: 'https://pmfby.gov.in/', yield_context: null,
    });
    wrap(<InsurancePage />);
    await waitFor(() => expect(screen.getByText(/waiting for an agriculture officer/)).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /Official PMFBY portal/ })).toHaveAttribute('href', 'https://pmfby.gov.in/');
  });
});
