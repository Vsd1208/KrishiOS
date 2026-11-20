/** The Fields page and farm summary show the farmer's records only; no sample plots or soil. */

import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import i18n from '@/i18n';
import { farmerApi } from '@/services/api/farmer';
import { FieldsPage } from '../FieldsPage';
import { FarmSummaryCard } from '@/features/farmer/components/FarmSummaryCard';
import type { Farmer, Field, FieldCrop } from '@/types/domain';

vi.mock('@/services/api/farmer', () => ({
  farmerApi: {
    getMe: vi.fn(), getFarmerById: vi.fn(), updateFarmer: vi.fn(), listFarmers: vi.fn(),
    listFields: vi.fn(), listCrops: vi.fn(), listFieldCrops: vi.fn(), listSoilSamples: vi.fn(),
  },
}));

const me: Farmer = {
  id: 9, farmer_code: 'c', full_name: 'Sita Devi', phone: '9', preferred_language: 'en',
  district_id: 1, village: 'Kothur', landholding_acres: 0, created_at: '', updated_at: '',
};
const field = (id: number, farmerId: number, name: string): Field => ({
  id, farmer_id: farmerId, field_name: name, area_acres: 1.5, latitude: null, longitude: null,
  soil_type: null, irrigation_type: null, created_at: '', updated_at: '',
});

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('en');
  vi.mocked(farmerApi.getMe).mockResolvedValue(me);
  vi.mocked(farmerApi.listCrops).mockResolvedValue([]);
  vi.mocked(farmerApi.listFieldCrops).mockResolvedValue([]);
  vi.mocked(farmerApi.listSoilSamples).mockResolvedValue([]);
});

describe('FieldsPage', () => {
  it('says no fields are registered instead of showing sample plots', async () => {
    vi.mocked(farmerApi.listFields).mockResolvedValue([field(1, 99, 'Someone else')]);
    wrap(<FieldsPage />);
    expect(await screen.findByText('No fields are registered for you yet', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/North Field|South Field|pH 6\.8|5\.5|Someone else/);
  });

  it('shows only the farmer’s own fields, with dashes for missing details', async () => {
    vi.mocked(farmerApi.listFields).mockResolvedValue([field(1, 9, 'River plot'), field(2, 99, 'Someone else')]);
    wrap(<FieldsPage />);
    expect(await screen.findByText('River plot', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByText('Someone else')).not.toBeInTheDocument();
    expect(screen.getAllByText('—')).toHaveLength(2);
    expect(await screen.findByText('No soil test recorded for this field.')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Black Soil|Borewell/);
  });
});

describe('FarmSummaryCard', () => {
  it('counts only growing or sown crops and shows no badge it cannot back up', () => {
    const crops = [{ status: 'Harvested' }, { status: 'Growing' }] as FieldCrop[];
    wrap(<FarmSummaryCard farmer={me} fields={[]} fieldCrops={crops} isLoading={false} />);
    const card = document.body.textContent ?? '';
    expect(card).not.toMatch(/Verified Farmer|District #/);
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
