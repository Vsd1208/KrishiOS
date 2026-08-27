import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReviewModal } from '../components/ReviewModal';
import type { AlertNotification } from '@/types/proactive';

const mockAlert: AlertNotification = {
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
};

describe('ReviewModal', () => {
  it('renders modal details and triggers approve action with notes', async () => {
    const handleAction = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <ReviewModal
        alert={mockAlert}
        isOpen={true}
        onClose={handleClose}
        onTakeAction={handleAction}
      />
    );

    expect(screen.getByText('Verify Agricultural Advisory')).toBeInTheDocument();
    expect(screen.getByText('Severe BPH Outbreak Warning')).toBeInTheDocument();
    expect(screen.getByText('Farmer #42')).toBeInTheDocument();

    const noteInput = screen.getByPlaceholderText(/Verified field observation/i);
    fireEvent.change(noteInput, { target: { value: 'Dosage verified with agronomist.' } });

    const approveButton = screen.getByRole('button', { name: /Approve & Send/i });
    fireEvent.click(approveButton);

    expect(handleAction).toHaveBeenCalledWith(
      101,
      expect.objectContaining({
        action: 'APPROVE',
        review_note: 'Dosage verified with agronomist.',
      })
    );
  });

  it('triggers reject action when Reject Advisory button is clicked', async () => {
    const handleAction = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <ReviewModal
        alert={mockAlert}
        isOpen={true}
        onClose={handleClose}
        onTakeAction={handleAction}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /Reject Advisory/i });
    fireEvent.click(rejectButton);

    expect(handleAction).toHaveBeenCalledWith(
      101,
      expect.objectContaining({
        action: 'REJECT',
      })
    );
  });
});
