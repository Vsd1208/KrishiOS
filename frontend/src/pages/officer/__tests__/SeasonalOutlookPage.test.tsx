import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import i18n from '@/i18n';
import { seasonalApi, type SeasonOutlook } from '@/services/api/seasonal';
import { SeasonalOutlookPage } from '../SeasonalOutlookPage';

vi.mock('@/services/api/seasonal', async (orig) => ({
  ...(await orig<typeof import('@/services/api/seasonal')>()),
  seasonalApi: { getOutlook: vi.fn() },
}));

const probs = { p_below: 0.185, p_near: 0.37, p_above: 0.444, lower_tercile: 736.8, upper_tercile: 872.1 };
const outlook: SeasonOutlook = {
  version: 'v1', season: 'JJAS', season_name: 'June-September', issue_month: 6, data_through: 2024,
  history: [1951, 2024], method: 'recent normals',
  variables: {
    rain: { unit: 'mm', test_rpss: 0.038, display: 'weak' },
    tmax: { unit: 'deg C', test_rpss: 0.19, display: 'show' },
    tmin: { unit: 'deg C', test_rpss: 0.01, display: 'withhold' },
  },
  districts: [
    { lgd_district_code: 509, district: 'Khammam', state: 'Telangana', variables: { rain: probs, tmax: probs, tmin: null } },
    { lgd_district_code: 1, district: 'Amritsar', state: 'Punjab', variables: { rain: probs, tmax: probs, tmin: null } },
  ],
};

const show = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <SeasonalOutlookPage />
    </QueryClientProvider>,
  );

describe('SeasonalOutlookPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
    vi.mocked(seasonalApi.getOutlook).mockResolvedValue(outlook);
  });

  it('shows districts, labels weak and withheld variables, and filters by state', async () => {
    show();
    expect(await screen.findByText('Khammam')).toBeInTheDocument();
    expect(screen.getByText('Weak signal')).toBeInTheDocument();
    expect(screen.getByText(/No reliable signal: see IMD/)).toBeInTheDocument();
    expect(screen.getAllByText('No reliable signal')).toHaveLength(2);
    expect(screen.getAllByTitle(/under 736.8 mm/).length).toBeGreaterThan(0);
    expect(screen.getByText(/IMD data up to 2024/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('State'), { target: { value: 'Punjab' } });
    const table = screen.getByRole('table');
    expect(within(table).queryByText('Khammam')).not.toBeInTheDocument();
    expect(within(table).getByText('Amritsar')).toBeInTheDocument();
  });

  it('asks for another season when a tab is chosen', async () => {
    show();
    await screen.findByText('Khammam');
    fireEvent.click(screen.getByRole('tab', { name: /Oct-Dec/ }));
    expect(seasonalApi.getOutlook).toHaveBeenLastCalledWith('OND');
  });
});
