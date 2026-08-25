import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WeatherWidget } from '../components/WeatherWidget';
import type { WeatherObservation, WeatherForecast } from '@/types/weather';

const mockWeather: WeatherObservation = {
  latitude: 17.247,
  longitude: 80.151,
  district: 'Khammam',
  state: 'Telangana',
  temperature_celsius: 32.4,
  relative_humidity_percent: 65,
  rainfall_mm: 0.0,
  wind_speed_mps: 2.8,
  weather_code: 1,
  weather_condition: 'Partly Cloudy',
};

const mockForecast: WeatherForecast = {
  latitude: 17.247,
  longitude: 80.151,
  district: 'Khammam',
  state: 'Telangana',
  forecast_days: [],
  summary: 'Dry weather expected for the next 4 days',
  spray_window_favorable: true,
  spray_window_reason: 'Favorable conditions (wind < 15 km/h, no rain)',
};

describe('WeatherWidget', () => {
  it('renders temperature, condition, humidity, and spray window advisory', () => {
    render(<WeatherWidget weather={mockWeather} forecast={mockForecast} />);

    expect(screen.getByText('32°')).toBeInTheDocument();
    expect(screen.getByText('Partly Cloudy')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('2.8 m/s')).toBeInTheDocument();
    expect(screen.getByText(/Spray Window: Favorable/)).toBeInTheDocument();
    expect(screen.getByText(/Favorable conditions/)).toBeInTheDocument();
  });

  it('renders unfavorable spray window when spray_window_favorable is false', () => {
    const unfavorableForecast: WeatherForecast = {
      ...mockForecast,
      spray_window_favorable: false,
      spray_window_reason: 'Heavy rainfall forecasted within 24 hours',
    };

    render(<WeatherWidget weather={mockWeather} forecast={unfavorableForecast} />);

    expect(screen.getByText(/Spray Window: Unfavorable/)).toBeInTheDocument();
    expect(screen.getByText(/Heavy rainfall forecasted/)).toBeInTheDocument();
  });
});
