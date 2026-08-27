import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GraphCandidateCard } from '../components/GraphCandidateCard';
import type { GraphCandidate } from '@/types/officer';

const mockCandidate: GraphCandidate = {
  id: 5,
  document_uuid: '880e8400-e29b-41d4-a716-446655440001',
  chunk_id: '880e8400-e29b-41d4-a716-446655440002',
  subject_label: 'Pest',
  subject_name: 'Brown Plant Hopper',
  predicate: 'INFESTS',
  object_label: 'Crop',
  object_name: 'Paddy',
  confidence: 0.94,
  review_status: 'PENDING',
  neo4j_rel_id: null,
};

describe('GraphCandidateCard', () => {
  it('renders subject, predicate, object, and triggers approve to graph', async () => {
    const handleReview = vi.fn().mockResolvedValue(undefined);

    render(
      <GraphCandidateCard
        candidate={mockCandidate}
        onReview={handleReview}
      />
    );

    expect(screen.getByText('Brown Plant Hopper')).toBeInTheDocument();
    expect(screen.getByText('INFESTS')).toBeInTheDocument();
    expect(screen.getByText('Paddy')).toBeInTheDocument();
    expect(screen.getByText('94%')).toBeInTheDocument();

    const approveButton = screen.getByRole('button', { name: /Approve to Graph/i });
    fireEvent.click(approveButton);

    expect(handleReview).toHaveBeenCalledWith(5, expect.objectContaining({ action: 'APPROVE' }));
  });
});
