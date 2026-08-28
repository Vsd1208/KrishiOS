import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IntelligenceCanvas } from '../components/IntelligenceCanvas';

describe('IntelligenceCanvas', () => {
  it('renders tab switcher and switches between GraphRAG, Telemetry, Vision, and Provenance tabs', () => {
    render(<IntelligenceCanvas crop="Paddy" district="Khammam" />);

    expect(screen.getByText(/Decision Intelligence Canvas/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /GraphRAG Chain/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Telemetry & Weather/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Vision Lab/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Scientific Sources/i })).toBeInTheDocument();

    // Click Telemetry Tab
    fireEvent.click(screen.getByRole('button', { name: /Telemetry & Weather/i }));
    expect(screen.getByText(/Live Field Telemetry & Weather Matrix/i)).toBeInTheDocument();

    // Click Vision Tab
    fireEvent.click(screen.getByRole('button', { name: /Vision Lab/i }));
    expect(screen.getByText(/Vision Intelligence Diagnostic Lab/i)).toBeInTheDocument();

    // Click Scientific Sources Tab
    fireEvent.click(screen.getByRole('button', { name: /Scientific Sources/i }));
    expect(screen.getByText(/Scientific Provenance & Citations/i)).toBeInTheDocument();
  });
});
