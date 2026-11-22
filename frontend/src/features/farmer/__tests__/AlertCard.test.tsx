import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import i18n from '@/i18n';
import { AlertCard } from '../components/AlertCard';
import type { AlertNotification } from '@/types/proactive';

const mockAlert: AlertNotification = {
  id: 42,
  uuid: '660e8400-e29b-41d4-a716-446655440001',
  decision_id: 10,
  farmer_id: 1,
  channel: 'IN_APP',
  title: 'Stem Borer Outbreak Detected',
  message: 'Pheromone trap counts exceed 10 moths/trap. Apply Cartap Hydrochloride 50 SP @ 2g/L.',
  priority: 'HIGH',
  status: 'SENT',
  reviewed_by: 'officer-uuid-123',
  review_note: 'Verified field incidence in neighbouring plot.',
  sent_at: '2026-08-25T10:00:00Z',
  acknowledged_at: null,
  created_at: '2026-08-25T10:00:00Z',
};

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('AlertCard', () => {
  it('renders alert title, message, risk level, and officer verified badge', () => {
    render(<AlertCard alert={mockAlert} />);

    expect(screen.getByText('Stem Borer Outbreak Detected')).toBeInTheDocument();
    expect(screen.getByText(/Cartap Hydrochloride/)).toBeInTheDocument();
    expect(screen.getByText(/High Risk/i)).toBeInTheDocument();
    expect(screen.getByText('Reviewed by officer')).toBeInTheDocument();
    expect(screen.getByText(/Verified field incidence/)).toBeInTheDocument();
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('triggers onAcknowledge when acknowledge button is clicked', () => {
    const handleAcknowledge = vi.fn();
    render(<AlertCard alert={mockAlert} onAcknowledge={handleAcknowledge} />);

    const ackButton = screen.getByRole('button', { name: /Mark as seen/i });
    fireEvent.click(ackButton);

    expect(handleAcknowledge).toHaveBeenCalledWith(42);
  });

  it('shows Acknowledged state when alert is already acknowledged', () => {
    const ackedAlert: AlertNotification = {
      ...mockAlert,
      status: 'ACKNOWLEDGED',
      acknowledged_at: '2026-08-25T11:00:00Z',
    };

    render(<AlertCard alert={ackedAlert} />);

    expect(screen.getByText('Seen')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mark as seen/i })).not.toBeInTheDocument();
  });
});
