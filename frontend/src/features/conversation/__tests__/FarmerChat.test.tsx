import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import i18n from '@/i18n';
import { conversationApi, type TurnResult } from '@/services/api/conversation';
import { FarmerChat } from '../FarmerChat';

vi.mock('@/services/api/conversation', () => ({
  conversationApi: {
    sendTurn: vi.fn(),
    sendVoiceTurn: vi.fn(),
    fetchAudio: vi.fn(),
    sendFeedback: vi.fn(),
  },
}));

const base: TurnResult = {
  conversation_id: 'c1',
  turn_id: 't1',
  status: 'answered',
  language: 'en',
  reply_text: 'Spray Tricyclazole 75% WP at 0.6 g/L.',
  reply_text_en: null,
  intent: 'disease',
  detected_language: 'en',
  clarification: null,
  citations: [{ title: 'ICAR Rice Package of Practices' }],
  slots: { crop: 'paddy' },
  translation_status: 'passthrough',
  requires_review: false,
  review_reason: null,
  providers: {},
  weather: null,
  audio_uuid: null,
  resumed_question: null,
  media: [],
};

const api = vi.mocked(conversationApi);

async function ask(text: string): Promise<void> {
  const box = screen.getByRole('textbox'); // language-independent: the UI follows the chat language
  fireEvent.change(box, { target: { value: text } });
  fireEvent.submit(box.closest('form') as HTMLFormElement);
  await waitFor(() => expect(api.sendTurn).toHaveBeenCalled());
}

describe('FarmerChat', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
  });

  it('sends the question in the selected language and shows the cited answer', async () => {
    api.sendTurn.mockResolvedValue(base);
    render(<FarmerChat initialLanguage="en" profile={{ crops: ['paddy'] }} />);
    fireEvent.click(screen.getByRole('button', { name: 'తెలుగు' }));
    await ask('my paddy has blast');

    expect(api.sendTurn).toHaveBeenCalledWith(
      expect.objectContaining({ text: 'my paddy has blast', language: 'te', profile: { crops: ['paddy'] } }),
    );
    expect(await screen.findByText(base.reply_text)).toBeInTheDocument();
    expect(screen.getByText('ICAR Rice Package of Practices')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveAttribute('placeholder', 'మీ ప్రశ్న టైప్ చేయండి');
  });

  it('shows clarification chips and sends the chosen value with the conversation id', async () => {
    api.sendTurn.mockResolvedValueOnce({
      ...base,
      status: 'clarification',
      reply_text: 'Which crop?',
      citations: [],
      clarification: {
        slot: 'crop',
        question: 'Which crop?',
        choices: [
          { value: 'cabbage', label: 'Cabbage' },
          { value: 'cauliflower', label: 'Cauliflower' },
        ],
      },
    });
    api.sendTurn.mockResolvedValueOnce({ ...base, turn_id: 't2', slots: { crop: 'cauliflower' } });
    render(<FarmerChat initialLanguage="en" />);
    await ask('gobhi pest');

    fireEvent.click(await screen.findByRole('button', { name: 'Cauliflower' }));
    await waitFor(() => expect(api.sendTurn).toHaveBeenCalledTimes(2));
    expect(api.sendTurn).toHaveBeenLastCalledWith(
      expect.objectContaining({ conversation_id: 'c1', choice: { slot: 'crop', value: 'cauliflower' } }),
    );
  });

  it('labels an unverified translation and a pending review', async () => {
    api.sendTurn.mockResolvedValue({ ...base, translation_status: 'blocked', requires_review: true });
    render(<FarmerChat initialLanguage="en" />);
    await ask('question');
    expect(await screen.findByText(/could not verify the translation/)).toBeInTheDocument();
  });

  it('thumbs-down asks for a reason and submits it', async () => {
    api.sendTurn.mockResolvedValue(base);
    api.sendFeedback.mockResolvedValue({});
    render(<FarmerChat initialLanguage="en" />);
    await ask('question');

    fireEvent.click(await screen.findByLabelText('Not helpful'));
    fireEvent.click(screen.getByRole('button', { name: 'Wrong' }));
    await waitFor(() => expect(api.sendFeedback).toHaveBeenCalledWith('t1', 'down', 'en', 'wrong'));
    expect(await screen.findByText('Thank you for your feedback.')).toBeInTheDocument();
  });

  it('shows verified how-to videos', async () => {
    api.sendTurn.mockResolvedValue({
      ...base,
      media: [
        {
          uuid: 'v1',
          kind: 'video',
          title: 'Blast management',
          url: 'https://example.org/v',
          source_org: 'ICAR',
          licence: 'CC BY',
          language: 'en',
          duration_s: 120,
          verified: true,
        },
      ],
    });
    render(<FarmerChat initialLanguage="en" />);
    await ask('question');
    const link = await screen.findByRole('link', { name: /Blast management/ });
    expect(link).toHaveAttribute('href', 'https://example.org/v');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
