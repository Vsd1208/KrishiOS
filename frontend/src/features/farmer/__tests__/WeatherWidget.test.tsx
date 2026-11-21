/** The dashboard weather card shows real readings or says there are none; never default numbers. */

import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { WeatherWidget } from '../components/WeatherWidget';
import type { WeatherObservation, WeatherForecast } from '@/types/weather';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('WeatherWidget', () => {
  it('says no reading is available instead of showing 29°C and a spray verdict', () => {
    render(<WeatherWidget weather={null} forecast={null} />);
    expect(screen.getByTestId('no-weather-reading')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/29|Partly Cloudy|68%|spray/i);
  });

  it('shows the readings and the forecast spray advice it was given', () => {
    const weather = {
      latitude: 0, longitude: 0, district: 'Khammam', temperature_celsius: 31.4, relative_humidity_percent: 55,
      rainfall_mm: 0, wind_speed_mps: 2.1, weather_code: 1, weather_condition: 'Clear',
    } as WeatherObservation;
    const forecast = { spray_window_favorable: false, spray_window_reason: 'Rain expected' } as WeatherForecast;
    render(<WeatherWidget weather={weather} forecast={forecast} />);
    expect(screen.getByText('31°C')).toBeInTheDocument();
    expect(screen.getByText('Clear')).toBeInTheDocument();
    expect(screen.getByText('55%')).toBeInTheDocument();
    expect(screen.getByText('2.1 m/s')).toBeInTheDocument();
    expect(screen.getByText('Avoid spraying today')).toBeInTheDocument();
    expect(screen.getByText('Rain expected')).toBeInTheDocument();
  });

  it('shows a favourable spray window when the forecast says so', () => {
    const forecast = { spray_window_favorable: true, spray_window_reason: 'Low wind, no rain' } as WeatherForecast;
    render(<WeatherWidget weather={null} forecast={forecast} />);
    expect(screen.getByText('OK to spray today')).toBeInTheDocument();
    expect(screen.getByText('Low wind, no rain')).toBeInTheDocument();
  });
});
