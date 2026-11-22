// Shows only what the answer carries; never sample or default data (UI polish).
import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { TelemetryMatrix } from '../components/canvas/TelemetryMatrix';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('TelemetryMatrix', () => {
  it('shows the readings it was given and a dash for missing ones', () => {
    render(<TelemetryMatrix telemetry={{ temperature_celsius: 31.8, spray_window_favorable: false }} district="Khammam" />);
    expect(screen.getByText('31.8°C')).toBeInTheDocument();
    expect(screen.getAllByText('—')).toHaveLength(3);
    expect(screen.getByText(/not suitable/)).toBeInTheDocument();
  });

  it('has no weather, spray verdict or mandi price when none was sent', () => {
    render(<TelemetryMatrix district="Khammam" crop="Paddy" />);
    expect(screen.getByTestId('no-weather')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/₹|Spray window|32\.5/);
  });
});
