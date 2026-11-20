// Shows only what the answer carries; never sample or default data (UI polish).
import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { ProvenanceExplorer } from '../components/canvas/ProvenanceExplorer';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('ProvenanceExplorer', () => {
  it('shows real citations and only the checks the backend reported', () => {
    render(
      <ProvenanceExplorer
        citations={[
          {
            citation_id: 'cit-1',
            source_title: 'Package of Practices for Rice',
            authority: 'State Agricultural University',
            page: 12,
            relevance_score: 0.95,
          },
        ]}
        evaluation={{ groundingRatio: 0.82, hallucinationDetected: true }}
      />,
    );
    expect(screen.getByText('Package of Practices for Rice')).toBeInTheDocument();
    expect(screen.getByText(/State Agricultural University · page 12/)).toBeInTheDocument();
    expect(screen.getByText('95% match')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
    expect(screen.getByText('Flagged')).toBeInTheDocument();
    expect(screen.queryByText('Consistency')).not.toBeInTheDocument();
  });

  it('says there are no sources instead of inventing them', () => {
    render(<ProvenanceExplorer />);
    expect(screen.getByTestId('no-sources')).toHaveTextContent('No sources were found for this answer.');
    expect(document.body.textContent).not.toMatch(/ICAR|ANGRAU|Cartap|%/);
  });
});
