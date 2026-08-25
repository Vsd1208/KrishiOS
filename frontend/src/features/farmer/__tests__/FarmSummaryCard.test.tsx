import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FarmSummaryCard } from '../components/FarmSummaryCard';
import type { Farmer, Field, FieldCrop } from '@/types/domain';

const mockFarmer: Farmer = {
  id: 1,
  farmer_code: '550e8400-e29b-41d4-a716-446655440000',
  full_name: 'Ramesh Patel',
  phone: '+919876543210',
  preferred_language: 'te',
  district_id: 12,
  village: 'Khammam Rural',
  landholding_acres: 4.5,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockFields: Field[] = [
  {
    id: 101,
    farmer_id: 1,
    field_name: 'North Plot',
    area_acres: 2.5,
    latitude: 17.247,
    longitude: 80.151,
    soil_type: 'Black Soil',
    irrigation_type: 'Borewell',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 102,
    farmer_id: 1,
    field_name: 'South Plot',
    area_acres: 2.0,
    latitude: 17.249,
    longitude: 80.153,
    soil_type: 'Red Sandy Loam',
    irrigation_type: 'Canal',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockFieldCrops: FieldCrop[] = [
  {
    id: 201,
    field_id: 101,
    crop_id: 1,
    season: 'Kharif',
    year: 2026,
    sowing_date: '2026-06-15',
    harvest_date: null,
    status: 'GROWING',
    created_at: '2026-06-15T00:00:00Z',
    updated_at: '2026-06-15T00:00:00Z',
  },
];

describe('FarmSummaryCard', () => {
  it('renders farmer name, village, landholding, and plot count', () => {
    render(
      <FarmSummaryCard
        farmer={mockFarmer}
        fields={mockFields}
        fieldCrops={mockFieldCrops}
      />
    );

    expect(screen.getByText('Ramesh Patel')).toBeInTheDocument();
    expect(screen.getByText(/Khammam Rural/)).toBeInTheDocument();
    expect(screen.getByText('4.5')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // 2 fields
    expect(screen.getByText('Verified Farmer')).toBeInTheDocument();
  });

  it('renders loading placeholder when isLoading is true', () => {
    render(
      <FarmSummaryCard
        farmer={null}
        fields={[]}
        fieldCrops={[]}
        isLoading={true}
      />
    );

    // Skeleton placeholders should be rendered with role="presentation"
    const skeletons = screen.getAllByRole('presentation', { hidden: true });
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
