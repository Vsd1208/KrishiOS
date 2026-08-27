import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BroadcastEventModal } from '../components/BroadcastEventModal';
import type { EventIngestResponse } from '@/types/officer';

const mockResponse: EventIngestResponse = {
  event_id: '990e8400-e29b-41d4-a716-446655440001',
  status: 'processed',
  decisions_count: 14,
  message: 'Event processed successfully. Generated 14 proactive decisions.',
};

describe('BroadcastEventModal', () => {
  it('renders template options and triggers onEmitEvent upon form submission', async () => {
    const handleEmit = vi.fn().mockResolvedValue(mockResponse);
    const handleClose = vi.fn();

    render(
      <BroadcastEventModal
        isOpen={true}
        onClose={handleClose}
        onEmitEvent={handleEmit}
      />
    );

    expect(screen.getByText('Broadcast Regional Advisory Event')).toBeInTheDocument();
    expect(screen.getByText('Pest / Disease Outbreak Warning')).toBeInTheDocument();

    const submitButton = screen.getByRole('button', { name: /Broadcast Event/i });
    fireEvent.click(submitButton);

    expect(handleEmit).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'disease.outbreak.detected',
      })
    );

    await waitFor(() => {
      expect(screen.getByText('Event Successfully Processed')).toBeInTheDocument();
    });
  });
});
