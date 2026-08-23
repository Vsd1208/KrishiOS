import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge } from '../ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('renders High Confidence for score >= 0.8', () => {
    render(<ConfidenceBadge confidence={0.88} />);
    expect(screen.getByLabelText(/high confidence/i)).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText(/88/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('title', 'AI confidence: 88%');
  });

  it('renders Medium Confidence for score between 0.5 and 0.79', () => {
    render(<ConfidenceBadge confidence={0.65} />);
    expect(screen.getByLabelText(/medium confidence/i)).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText(/65/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('title', 'AI confidence: 65%');
  });

  it('renders Low Confidence for score < 0.5', () => {
    render(<ConfidenceBadge confidence={0.35} />);
    expect(screen.getByLabelText(/low confidence/i)).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText(/35/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('title', 'AI confidence: 35%');
  });
});
