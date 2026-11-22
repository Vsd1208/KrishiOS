import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import i18n from '@/i18n';
import { AdvisoryActionToolbar } from '../components/AdvisoryActionToolbar';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('AdvisoryActionToolbar', () => {
  it('prints and hands the question to the officer flow without claiming it was sent', () => {
    const handleEscalate = vi.fn();
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});

    render(<AdvisoryActionToolbar advisoryText="Apply bio-pesticide" crop="Paddy" onEscalate={handleEscalate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Print' }));
    expect(print).toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Ask an officer' }));
    expect(handleEscalate).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).not.toMatch(/Dispatched|Saved to Notebook/);
    print.mockRestore();
  });

  it('has no officer button when there is nowhere to send the question', () => {
    render(<AdvisoryActionToolbar advisoryText="x" />);
    expect(screen.queryByRole('button', { name: 'Ask an officer' })).not.toBeInTheDocument();
  });
});
