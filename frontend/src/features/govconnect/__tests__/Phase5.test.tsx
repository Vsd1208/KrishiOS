import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import i18n from '@/i18n';
import { feedApi, type DistrictFeed } from '@/services/api/govconnect';
import { conversationApi } from '@/services/api/conversation';
import { WeatherFeedCard } from '../WeatherFeedCard';
import { FarmerChat } from '@/features/conversation/FarmerChat';

vi.mock('@/services/api/govconnect', async (orig) => ({
  ...(await orig<typeof import('@/services/api/govconnect')>()),
  feedApi: { weatherFeed: vi.fn(), status: vi.fn(), pushConfig: vi.fn() },
}));
vi.mock('@/services/api/conversation', () => ({
  conversationApi: { sendTurn: vi.fn(), sendVoiceTurn: vi.fn(), fetchAudio: vi.fn(), sendFeedback: vi.fn() },
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const feed: DistrictFeed = {
  lgd_district_code: 509,
  district_name: 'Khammam',
  state_name: 'Telangana',
  official_warnings: [
    {
      uuid: 'w1', status: 'published', title: 'Heavy rainfall warning',
      authority: 'India Meteorological Department (Hyderabad)', authority_level: 'state',
      severity: 'HIGH', hazard_type: 'heavy_rain', original_language: 'en', issued_at: null,
      valid_from: null, valid_to: '2026-11-15T12:00:00Z', district_codes: [509], block_codes: [],
      crops: [], source_type: 'feed', publish_at: null, published_at: null, index_state: null,
      created_at: null,
    },
  ],
  forecast: [
    { date: '2026-11-14', temperature_min_celsius: 18, temperature_max_celsius: 30.4,
      precipitation_probability_percent: 80, precipitation_sum_mm: 42.2, max_wind_speed_mps: 2,
      weather_condition: 'Rainy' },
  ],
  spray: { favorable: false, reason: '80% chance of rain' },
  crosscheck: { status: 'disagree', reasons: ['rainfall totals differ (40 vs 5 mm)'] },
  providers: { forecast: 'open-meteo-v1', reference: 'nasa-power-daily' },
  fetched_at: '2026-11-14T06:00:00Z',
  age_minutes: 12,
  stale: false,
  attribution: ['Forecast: Open-Meteo (CC BY 4.0)', 'Cross-check: NASA POWER'],
};

describe('Weather feed card', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('shows the official warning, the forecast and an honest cross-check', async () => {
    vi.mocked(feedApi.weatherFeed).mockResolvedValue([feed]);
    wrap(<WeatherFeedCard />);
    expect(await screen.findByText('Heavy rainfall warning')).toBeInTheDocument();
    expect(screen.getByText(/India Meteorological Department/)).toBeInTheDocument();
    expect(screen.getByText('42 mm')).toBeInTheDocument();
    expect(screen.getByText('Sources disagree')).toBeInTheDocument();
    expect(screen.getByText(/rainfall totals differ/)).toBeInTheDocument();
    expect(screen.getByText('Avoid spraying today')).toBeInTheDocument();
    expect(screen.getByText('Updated 12 min ago')).toBeInTheDocument();
    expect(screen.getByText(/Official warnings above always take priority/)).toBeInTheDocument();
  });
});

describe('Offline question queue', () => {
  const setOnline = (v: boolean) =>
    Object.defineProperty(window.navigator, 'onLine', { configurable: true, get: () => v });

  beforeEach(async () => {
    vi.clearAllMocks();
    localStorage.clear();
    await i18n.changeLanguage('en');
  });
  afterEach(() => setOnline(true));

  it('keeps a question typed offline and sends it when back online', async () => {
    vi.mocked(conversationApi.sendTurn).mockResolvedValue({
      conversation_id: 'c1', turn_id: 't1', status: 'answered', language: 'en',
      reply_text: 'Drain the field.', reply_text_en: null, intent: 'advisory',
      detected_language: 'en', clarification: null, citations: [], slots: {},
      translation_status: null, requires_review: false, review_reason: null, providers: {},
      weather: null, audio_uuid: null, resumed_question: null, media: [],
    });
    setOnline(false);
    render(<FarmerChat initialLanguage="en" />);
    const box = screen.getByRole('textbox');
    fireEvent.change(box, { target: { value: 'Water is standing in my field' } });
    fireEvent.submit(box.closest('form') as HTMLFormElement);
    expect(await screen.findByText(/will send when you are connected/)).toBeInTheDocument();
    expect(conversationApi.sendTurn).not.toHaveBeenCalled();

    setOnline(true);
    await act(async () => {
      window.dispatchEvent(new Event('online'));
    });
    await waitFor(() =>
      expect(conversationApi.sendTurn).toHaveBeenCalledWith(
        expect.objectContaining({ text: 'Water is standing in my field' }),
      ),
    );
    expect(await screen.findByText('Drain the field.')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('krishios_offline_questions') ?? '[]')).toEqual([]);
  });
});
