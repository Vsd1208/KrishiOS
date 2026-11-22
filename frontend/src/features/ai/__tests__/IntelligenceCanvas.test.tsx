import { beforeEach, describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import i18n from '@/i18n';
import { IntelligenceCanvas } from '../components/IntelligenceCanvas';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('IntelligenceCanvas', () => {
  it('switches between the knowledge graph, weather, photo and sources tabs', () => {
    render(<IntelligenceCanvas crop="Paddy" district="Khammam" />);

    expect(screen.getByText('Answer details')).toBeInTheDocument();
    expect(screen.getByText('This answer did not use the knowledge graph.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Weather' }));
    expect(screen.getByText('Weather used in this answer')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Photo' }));
    expect(screen.getByText('Your photo')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Sources' }));
    expect(screen.getByText('Sources for this answer')).toBeInTheDocument();
  });

  it('shows the tabs in Telugu', async () => {
    await i18n.changeLanguage('te');
    render(<IntelligenceCanvas crop="Paddy" district="Khammam" />);
    expect(screen.getByRole('button', { name: 'వాతావరణం' })).toBeInTheDocument();
  });
});
