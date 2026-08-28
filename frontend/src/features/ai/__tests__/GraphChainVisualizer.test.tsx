import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GraphChainVisualizer } from '../components/canvas/GraphChainVisualizer';

describe('GraphChainVisualizer', () => {
  it('renders GraphRAG knowledge graph title and reasoning chain nodes', () => {
    render(
      <GraphChainVisualizer
        graphPaths={[
          {
            path: 'Paddy -> HAS_PEST -> Yellow Stem Borer -> CONTROLLED_BY -> Cartap Hydrochloride',
            confidence: 0.94,
            relationship: 'AGRONOMIC_RULE',
          },
        ]}
      />
    );

    expect(screen.getByText(/GraphRAG Agronomic Knowledge Graph/i)).toBeInTheDocument();
    expect(screen.getByText('Paddy')).toBeInTheDocument();
    expect(screen.getByText('Yellow Stem Borer')).toBeInTheDocument();
    expect(screen.getByText('Cartap Hydrochloride')).toBeInTheDocument();
    expect(screen.getByText(/94% Fact Coherence/i)).toBeInTheDocument();
  });
});
