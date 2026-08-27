import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReviewQueueTable } from '../components/ReviewQueueTable';
import type { AlertNotification } from '@/types/proactive';

const mockReviews: AlertNotification[] = [
  {
    id: 101,
    uuid: '770e8400-e29b-41d4-a716-446655440001',
    decision_id: 1,
    farmer_id: 42,
    channel: 'SMS',
    title: 'Severe BPH Outbreak Warning',
    message: 'Brown Plant Hopper count has crossed 15 per hill. Spray Pymetrozine 50 WG @ 0.6 g/L immediately.',
    priority: 'URGENT',
    status: 'PENDING_REVIEW',
    reviewed_by: null,
    review_note: null,
    sent_at: null,
    acknowledged_at: null,
    created_at: '2026-08-27T10:00:00Z',
  },
];

describe('ReviewQueueTable', () => {
  it('renders pending review items with priority and farmer badge', () => {
    render(
      <ReviewQueueTable
        reviews={mockReviews}
        onTakeAction={vi.fn()}
      />
    );

    expect(screen.getByText(/Pending Advisory Queue \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText('Severe BPH Outbreak Warning')).toBeInTheDocument();
    expect(screen.getByText('Farmer #42')).toBeInTheDocument();
    expect(screen.getByText(/Critical/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Inspect & Verify/i })).toBeInTheDocument();
  });

  it('renders empty queue message when no reviews are pending', () => {
    render(
      <ReviewQueueTable
        reviews={[]}
        onTakeAction={vi.fn()}
      />
    );

    expect(screen.getByText('Review Queue Clear')).toBeInTheDocument();
  });
});
