/**
 * A farmer sees and saves only their own data: the profile comes from /farmers/me, the alert
 * switches are saved to the real preferences endpoint, and the dashboard's crop card shows the
 * farmer's recorded crop instead of a fixed paddy example.
 */

import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import i18n from '@/i18n';
import { farmerApi } from '@/services/api/farmer';
import { alertsApi } from '@/services/api/alerts';
import { ApiError } from '@/types/api';
import { ProfilePage } from '../ProfilePage';
import type { Farmer } from '@/types/domain';
import type { NotificationPreference } from '@/types/proactive';

vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ user: { uuid: 'u', role: 'farmer', permissions: [] }, logout: vi.fn() }) }));
vi.mock('@/features/govconnect/LocationsCard', () => ({ LocationsCard: () => null }));
vi.mock('@/features/govconnect/PushOptIn', () => ({ PushOptIn: () => null }));
vi.mock('@/services/api/farmer', () => ({
  farmerApi: {
    getMe: vi.fn(), getFarmerById: vi.fn(), updateFarmer: vi.fn(), listFarmers: vi.fn(),
    listFields: vi.fn(), listCrops: vi.fn(), listFieldCrops: vi.fn(),
  },
}));
vi.mock('@/services/api/alerts', () => ({ alertsApi: { getPreferences: vi.fn(), updatePreferences: vi.fn() } }));

const me: Farmer = {
  id: 9, farmer_code: 'c', full_name: 'Sita Devi', phone: '9000000009', preferred_language: 'hi',
  district_id: 1, village: 'Kothur', landholding_acres: 2, created_at: '', updated_at: '',
};
const pref: NotificationPreference = {
  id: 1, farmer_id: 9, preferred_channel: 'in_app' as NotificationPreference['preferred_channel'],
  preferred_language: 'hi', min_severity: 'low' as NotificationPreference['min_severity'],
  quiet_hours_enabled: true, quiet_hours_start: '21:00', quiet_hours_end: '05:00',
  enable_weather_alerts: true, enable_disease_alerts: true, enable_market_alerts: true, enable_scheme_alerts: true,
  created_at: '', updated_at: '',
};

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('en');
});

describe('ProfilePage', () => {
  it('shows the signed-in farmer from /farmers/me, never the first farmer in the list', async () => {
    vi.mocked(farmerApi.getMe).mockResolvedValue(me);
    vi.mocked(alertsApi.getPreferences).mockResolvedValue(pref);
    wrap(<ProfilePage />);
    expect(await screen.findByText('Sita Devi')).toBeInTheDocument();
    expect(screen.getByText('9000000009')).toBeInTheDocument();
    expect(farmerApi.listFarmers).not.toHaveBeenCalled();
  });

  it('saves the alert switches with the rest of the preferences unchanged', async () => {
    vi.mocked(farmerApi.getMe).mockResolvedValue(me);
    vi.mocked(alertsApi.getPreferences).mockResolvedValue(pref);
    vi.mocked(alertsApi.updatePreferences).mockResolvedValue({ ...pref, enable_market_alerts: false });
    wrap(<ProfilePage />);

    const save = await screen.findByRole('button', { name: 'Save alert choices' });
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: /Mandi price alerts/ }));
    fireEvent.click(save);

    await waitFor(() => expect(alertsApi.updatePreferences).toHaveBeenCalledTimes(1));
    const sent = vi.mocked(alertsApi.updatePreferences).mock.calls[0][0];
    expect(sent).toMatchObject({ enable_market_alerts: false, quiet_hours_start: '21:00', quiet_hours_enabled: true });
    expect(sent).not.toHaveProperty('id');
    expect(await screen.findByText('Saved')).toBeInTheDocument();
  });

  it('saves the language to the farmer profile', async () => {
    vi.mocked(farmerApi.getMe).mockResolvedValue(me);
    vi.mocked(alertsApi.getPreferences).mockResolvedValue(pref);
    vi.mocked(farmerApi.updateFarmer).mockResolvedValue({ ...me, preferred_language: 'te' });
    wrap(<ProfilePage />);
    await screen.findByText('Sita Devi');
    fireEvent.click(screen.getByRole('radio', { name: /Telugu/ }));
    await waitFor(() => expect(farmerApi.updateFarmer).toHaveBeenCalledWith(9, { preferred_language: 'te' }));
    await i18n.changeLanguage('en');
  });

  it('shows dashes and no switches when no farmer profile is linked', async () => {
    vi.mocked(farmerApi.getMe).mockRejectedValue(new ApiError(404, 'not_found', 'none'));
    wrap(<ProfilePage />);
    expect(await screen.findByText('No farmer profile is linked to this login')).toBeInTheDocument();
    expect(screen.getAllByText('—')).toHaveLength(2);
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/98765|#101/);
  });
});
