import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import i18n from '@/i18n';
import { surveillanceApi } from '@/services/api/surveillance';
import { VisionCard } from '../VisionCard';
import { PhotoButton } from '../PhotoButton';
import { OutbreakMapPage } from '@/pages/officer/OutbreakMapPage';

vi.mock('@/services/api/surveillance', async (orig) => ({
  ...(await orig<typeof import('@/services/api/surveillance')>()),
  surveillanceApi: { heatmap: vi.fn(), outbreaks: vi.fn() },
}));

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

describe('photo questions', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
  });

  it('shows findings as possibilities, never a diagnosis', () => {
    wrap(
      <VisionCard
        vision={{
          crop: 'tomato', crop_confirmed_by_farmer: true, crop_candidates: [['tomato', 0.4]],
          candidate_conditions: [{ name: 'early blight', confidence: 0.71 }],
          model_name: 'krishios-vision-efficientnet_b0', model_version: 'v1', official: false,
        }}
      />,
    );
    expect(screen.getByText('early blight')).toBeInTheDocument();
    expect(screen.getByText('71%')).toBeInTheDocument();
    expect(screen.getByText(/not a diagnosis/)).toBeInTheDocument();
    expect(screen.getByText(/crop confirmed by you/)).toBeInTheDocument();
  });

  it('passes the picked photo on', async () => {
    const onPicked = vi.fn();
    wrap(<PhotoButton onPicked={onPicked} />);
    const file = new File([new Uint8Array([1, 2, 3])], 'leaf.jpg', { type: 'image/jpeg' });
    fireEvent.change(screen.getByTestId('photo-input'), { target: { files: [file] } });
    await waitFor(() => expect(onPicked).toHaveBeenCalledTimes(1));
  });

  it('lists possible outbreaks and the weekly grid for officers', async () => {
    const cell = {
      lgd_district_code: 509, district_name: 'Khammam', state_name: 'Telangana', crop: 'paddy',
      crop_name: 'Paddy (Rice)', condition: 'blast', week_start: '2026-11-16', reporters: 4,
    };
    vi.mocked(surveillanceApi.heatmap).mockResolvedValue({
      weeks: 8, note: 'Unverified model findings', cells: [{ ...cell, mean_confidence: 0.8 }],
    });
    vi.mocked(surveillanceApi.outbreaks).mockResolvedValue({
      week_start: '2026-11-16', items: [{ ...cell, baseline: 1 }],
    });
    wrap(<OutbreakMapPage />);
    await waitFor(() => expect(screen.getByText(/4 farmers/)).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /Review outbreak drafts/ })).toHaveAttribute('href', '/officer/bulletins');
    expect(screen.getAllByText('blast').length).toBeGreaterThan(0);
  });
});
