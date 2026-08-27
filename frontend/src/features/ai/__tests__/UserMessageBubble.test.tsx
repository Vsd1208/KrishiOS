import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserMessageBubble } from '../components/UserMessageBubble';
import type { UserMessageContent } from '../types/conversation';

const mockContent: UserMessageContent = {
  text: 'నా వరి ఆకులు పసుపుగా మారుతున్నాయి. రేపు వర్షం పడుతుందా?',
  language: 'te',
};

describe('UserMessageBubble', () => {
  it('renders Telugu text and language badge', () => {
    render(<UserMessageBubble content={mockContent} timestamp="10:30 AM" />);

    expect(
      screen.getByText('నా వరి ఆకులు పసుపుగా మారుతున్నాయి. రేపు వర్షం పడుతుందా?')
    ).toBeInTheDocument();
    expect(screen.getByText(/Telugu Mode/i)).toBeInTheDocument();
    expect(screen.getByText('10:30 AM')).toBeInTheDocument();
  });
});
