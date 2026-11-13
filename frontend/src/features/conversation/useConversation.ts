import { useCallback, useRef, useState } from 'react';

import {
  conversationApi,
  type BotLanguage,
  type ClarificationChoice,
  type FarmerProfileHint,
  type FeedbackReason,
  type TurnResult,
} from '@/services/api/conversation';
import { ApiError } from '@/types/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  text: string;
  result?: TurnResult;
  feedback?: 'up' | 'down';
}

export interface UseConversationOptions {
  initialLanguage?: BotLanguage;
  profile?: FarmerProfileHint | null;
  actAsFarmerId?: number | null;
}

let counter = 0;
const nextId = (): string => `m${Date.now()}-${(counter += 1)}`;

export function useConversation({
  initialLanguage = 'en',
  profile,
  actAsFarmerId = null,
}: UseConversationOptions = {}) {
  const [language, setLanguage] = useState<BotLanguage>(initialLanguage);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speak, setSpeak] = useState(false);
  const conversationId = useRef<string | null>(null);

  const push = (m: ChatMessage): void => setMessages((prev) => [...prev, m]);

  const run = useCallback(
    async (userText: string | null, call: () => Promise<TurnResult>): Promise<void> => {
      setBusy(true);
      setError(null);
      const userId = nextId();
      if (userText) push({ id: userId, role: 'user', text: userText });
      try {
        const result = await call();
        conversationId.current = result.conversation_id;
        if (result.transcript !== undefined) {
          push({ id: userId, role: 'user', text: result.transcript || '…' });
        }
        push({ id: result.turn_id || nextId(), role: 'bot', text: result.reply_text, result });
      } catch (e) {
        setError(e instanceof ApiError ? e.message : 'error');
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const sendText = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return Promise.resolve();
      return run(trimmed, () =>
        conversationApi.sendTurn({
          text: trimmed,
          language,
          conversation_id: conversationId.current,
          speak,
          profile: profile ?? null,
          act_as_farmer_id: actAsFarmerId,
        }),
      );
    },
    [actAsFarmerId, language, profile, run, speak],
  );

  const choose = useCallback(
    (slot: string, choice: ClarificationChoice) =>
      run(choice.label, () =>
        conversationApi.sendTurn({
          language,
          conversation_id: conversationId.current,
          choice: { slot, value: choice.value },
          speak,
          profile: profile ?? null,
          act_as_farmer_id: actAsFarmerId,
        }),
      ),
    [actAsFarmerId, language, profile, run, speak],
  );

  const sendVoice = useCallback(
    (audio: Blob) =>
      run(null, () =>
        conversationApi.sendVoiceTurn(audio, language, conversationId.current, speak, actAsFarmerId),
      ),
    [actAsFarmerId, language, run, speak],
  );

  const rate = useCallback(
    async (messageId: string, rating: 'up' | 'down', reason?: FeedbackReason) => {
      const msg = messages.find((m) => m.id === messageId);
      if (!msg?.result) return;
      await conversationApi.sendFeedback(msg.result.turn_id, rating, language, reason);
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m)));
    },
    [language, messages],
  );

  const reset = useCallback(() => {
    conversationId.current = null;
    setMessages([]);
    setError(null);
  }, []);

  return {
    language,
    setLanguage,
    messages,
    busy,
    error,
    speak,
    setSpeak,
    sendText,
    sendVoice,
    choose,
    rate,
    reset,
  };
}
