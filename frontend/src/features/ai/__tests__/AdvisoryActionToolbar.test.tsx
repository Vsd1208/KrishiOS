import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AdvisoryActionToolbar } from '../components/AdvisoryActionToolbar';

describe('AdvisoryActionToolbar', () => {
  it('handles save to notebook, print, and escalate to officer', () => {
    const handleEscalate = vi.fn();

    render(
      <AdvisoryActionToolbar
        advisoryText="Apply recommended bio-pesticide"
        crop="Paddy"
        onEscalate={handleEscalate}
      />
    );

    const saveBtn = screen.getByRole('button', { name: /Save to Notebook/i });
    expect(saveBtn).toBeInTheDocument();
    fireEvent.click(saveBtn);
    expect(screen.getByText(/Saved to Notebook/i)).toBeInTheDocument();

    const escalateBtn = screen.getByRole('button', { name: /Escalate to Officer/i });
    expect(escalateBtn).toBeInTheDocument();
    fireEvent.click(escalateBtn);
    expect(handleEscalate).toHaveBeenCalled();
    expect(screen.getByText(/Dispatched to Officer/i)).toBeInTheDocument();
  });
});
