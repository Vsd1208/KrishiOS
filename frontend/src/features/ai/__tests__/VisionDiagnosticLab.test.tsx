import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VisionDiagnosticLab } from '../components/canvas/VisionDiagnosticLab';

describe('VisionDiagnosticLab', () => {
  it('renders vision diagnostic lab title and candidate pathogen conditions', () => {
    render(<VisionDiagnosticLab crop="Paddy" />);

    expect(screen.getByText(/Vision Intelligence Diagnostic Lab/i)).toBeInTheDocument();
    expect(screen.getByText(/Yellow Stem Borer/i)).toBeInTheDocument();
    expect(screen.getByText(/Bacterial Leaf Blight/i)).toBeInTheDocument();
    expect(screen.getByText(/Candidate Conditions for Paddy:/i)).toBeInTheDocument();
  });
});
