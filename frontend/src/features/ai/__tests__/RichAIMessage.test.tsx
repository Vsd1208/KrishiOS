import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RichAIMessage } from '../components/RichAIMessage';
import type { AIMessageContent } from '../types/conversation';

const mockAIContent: AIMessageContent = {
  text: 'Based on your field symptoms, apply Cartap Hydrochloride 50 SP @ 2g/L. Weather is dry and favorable for spraying.',
  confidence: 0.92,
  grounded: true,
  riskSeverity: 'HIGH',
  liveContext: {
    temperatureCelsius: 32.4,
    weatherCondition: 'Partly Cloudy',
    sprayWindowFavorable: true,
  },
  citations: [
    {
      citation_id: 'cit-1',
      source_title: 'ICAR Standard Package of Practices for Wetland Paddy',
      authority: 'ICAR Research Complex',
      document_type: 'Agronomy Bulletin',
      snippet: 'Effective chemical control for stem borer in vegetative phase.',
      relevance_score: 0.94,
    },
  ],
  suggestedFollowUps: [
    'What is the recommended spray dosage per acre?',
    'Will rain in next 48h wash away the chemical spray?',
  ],
};

describe('RichAIMessage', () => {
  it('renders advisory text, confidence score, risk badge, and live weather context', () => {
    render(
      <RichAIMessage
        content={mockAIContent}
        messageId="ai-1"
        timestamp="10:31 AM"
      />
    );

    expect(screen.getByText(/Based on your field symptoms/i)).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText(/High Risk/i)).toBeInTheDocument();
    expect(screen.getByText(/Weather:/i)).toBeInTheDocument();
    expect(screen.getByText(/Spray Window: Favorable/i)).toBeInTheDocument();
  });

  it('expands "Why this answer?" evidence drawer and displays ICAR citations', () => {
    render(
      <RichAIMessage
        content={mockAIContent}
        messageId="ai-1"
        timestamp="10:31 AM"
      />
    );

    const evidenceToggle = screen.getByText(/Why this answer\?/i);
    fireEvent.click(evidenceToggle);

    expect(
      screen.getByText('ICAR Standard Package of Practices for Wetland Paddy')
    ).toBeInTheDocument();
    expect(screen.getByText('ICAR Research Complex')).toBeInTheDocument();
  });

  it('triggers onSpeak when Listen button is clicked', () => {
    const handleSpeak = vi.fn();

    render(
      <RichAIMessage
        content={mockAIContent}
        messageId="ai-1"
        timestamp="10:31 AM"
        onSpeak={handleSpeak}
      />
    );

    const listenButton = screen.getByRole('button', { name: /Listen/i });
    fireEvent.click(listenButton);

    expect(handleSpeak).toHaveBeenCalledWith(
      mockAIContent.text,
      'te-IN',
      'ai-1',
      1
    );
  });

  it('triggers onSelectFollowUp when a suggestion chip is clicked', () => {
    const handleFollowUp = vi.fn();

    render(
      <RichAIMessage
        content={mockAIContent}
        messageId="ai-1"
        timestamp="10:31 AM"
        onSelectFollowUp={handleFollowUp}
      />
    );

    const followUpChip = screen.getByText('What is the recommended spray dosage per acre?');
    fireEvent.click(followUpChip);

    expect(handleFollowUp).toHaveBeenCalledWith(
      'What is the recommended spray dosage per acre?'
    );
  });
});
