import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TelemetryMatrix } from '../components/canvas/TelemetryMatrix';

describe('TelemetryMatrix', () => {
  it('renders air temp, humidity, spray window feasibility, and mandi price ticker', () => {
    render(
      <TelemetryMatrix
        telemetry={{
          temperature_celsius: 31.8,
          relative_humidity_percent: 64,
          wind_speed_kmh: 9.5,
          rainfall_mm: 0.0,
          spray_window_favorable: true,
          spray_window_reason: 'Optimal conditions for spraying',
        }}
        district="Khammam"
        crop="Paddy"
      />
    );

    expect(screen.getByText('31.8°C')).toBeInTheDocument();
    expect(screen.getByText('64%')).toBeInTheDocument();
    expect(screen.getByText('9.5 km/h')).toBeInTheDocument();
    expect(screen.getByText(/Spray Window: Favorable/i)).toBeInTheDocument();
    expect(screen.getByText(/Live Mandi Commodity Price/i)).toBeInTheDocument();
  });
});
