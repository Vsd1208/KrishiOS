import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProvenanceExplorer } from '../components/canvas/ProvenanceExplorer';

describe('ProvenanceExplorer', () => {
  it('renders ICAR citations and AI grounding evaluation metrics', () => {
    render(
      <ProvenanceExplorer
        citations={[
          {
            citation_id: 'cit-pop-1',
            source_title: 'ICAR Standard Package of Practices for Rice',
            authority: 'ICAR National Rice Research Institute',
            snippet: 'Cartap Hydrochloride 50 SP @ 2g/L is recommended.',
            relevance_score: 0.95,
          },
        ]}
        evaluation={{
          grounding_ratio: 0.96,
          coherence_score: 0.94,
          hallucination_detected: false,
        }}
      />
    );

    expect(screen.getByText(/Scientific Provenance & Citations/i)).toBeInTheDocument();
    expect(screen.getByText('ICAR Standard Package of Practices for Rice')).toBeInTheDocument();
    expect(screen.getByText(/ICAR National Rice Research Institute/i)).toBeInTheDocument();
    expect(screen.getByText('96%')).toBeInTheDocument();
    expect(screen.getByText(/Passed/i)).toBeInTheDocument();
  });
});
