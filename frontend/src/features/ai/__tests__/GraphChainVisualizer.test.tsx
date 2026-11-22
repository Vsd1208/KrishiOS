// Shows only what the answer carries; never sample or default data (UI polish).
import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { GraphChainVisualizer } from '../components/canvas/GraphChainVisualizer';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('GraphChainVisualizer', () => {
  it('draws the chains the answer used', () => {
    render(
      <GraphChainVisualizer
        graphPaths={[{ path: 'Paddy -> HAS_PEST -> Stem borer', confidence: 0.9, relationship: 'AGRONOMIC_RULE' }]}
      />,
    );
    expect(screen.getByText('Paddy')).toBeInTheDocument();
    expect(screen.getByText('Stem borer')).toBeInTheDocument();
    expect(screen.getByText('90% confidence')).toBeInTheDocument();
  });

  it('shows an empty state when no graph was used', () => {
    render(<GraphChainVisualizer crop="Paddy" />);
    expect(screen.getByTestId('no-graph')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Cartap|Urea|Stem Borer/i);
  });
});
