import { useCallback, useEffect, useRef, useState } from 'react';

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
  /** Typed while offline; sent automatically when the connection returns (F3). */
  queued?: boolean;
}

const QUEUE_KEY = 'krishios_offline_questions';
const MAX_QUEUE = 10;

interface QueuedQuestion {
  id: string;
  text: string;
  language: BotLanguage;
}

/** Questions stay on this device only (localStorage) until they can be sent. */
function readQueue(): QueuedQuestion[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? '[]') as QueuedQuestion[];
  } catch {
    return [];
  }
}

function writeQueue(q: QueuedQuestion[]): void {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q.slice(-MAX_QUEUE)));
  } catch {
    /* storage unavailable: the question is still shown, just not persisted */
  }
}

export interface UseConversationOptions {
  initialLanguage?: BotLanguage;
  profile?: FarmerProfileHint | null;
  actAsFarmerId?: number | null;
  bulletinUuid?: string | null;
}

let counter = 0;
const nextId = (): string => `m${Date.now()}-${(counter += 1)}`;

export function useConversation({
  initialLanguage = 'en',
  profile,
  actAsFarmerId = null,
  bulletinUuid = null,
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
        if (result.conversation_id) conversationId.current = result.conversation_id;
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
      if (typeof navigator !== 'undefined' && navigator.onLine === false) {
        const id = nextId();
        writeQueue([...readQueue(), { id, text: trimmed, language }]);
        push({ id, role: 'user', text: trimmed, queued: true });
        return Promise.resolve();
      }
      return run(trimmed, () =>
        conversationApi.sendTurn({
          text: trimmed,
          language,
          conversation_id: conversationId.current,
          speak,
          profile: profile ?? null,
          act_as_farmer_id: actAsFarmerId,
          bulletin_uuid: bulletinUuid,
        }),
      );
    },
    [actAsFarmerId, bulletinUuid, language, profile, run, speak],
  );

  // Send questions queued while offline, oldest first, once the connection returns.
  useEffect(() => {
    const flush = async (): Promise<void> => {
      const queue = readQueue();
      if (queue.length === 0) return;
      writeQueue([]);
      for (const q of queue) {
        setMessages((prev) => prev.map((m) => (m.id === q.id ? { ...m, queued: false } : m)));
        await run(null, () =>
          conversationApi.sendTurn({
            text: q.text,
            language: q.language,
            conversation_id: conversationId.current,
            profile: profile ?? null,
            act_as_farmer_id: actAsFarmerId,
            bulletin_uuid: bulletinUuid,
          }),
        );
      }
    };
    window.addEventListener('online', flush);
    if (navigator.onLine) void flush();
    return () => window.removeEventListener('online', flush);
  }, [actAsFarmerId, bulletinUuid, profile, run]);

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
          bulletin_uuid: bulletinUuid,
        }),
      ),
    [actAsFarmerId, bulletinUuid, language, profile, run, speak],
  );

  const sendVoice = useCallback(
    (audio: Blob) =>
      run(null, () =>
        conversationApi.sendVoiceTurn(audio, language, conversationId.current, speak, actAsFarmerId),
      ),
    [actAsFarmerId, language, run, speak],
  );

  /** Photo question: the local model reads the crop; the bot asks to confirm when unsure. */
  const sendPhoto = useCallback(
    (photo: Blob, text = '', label = '📷') =>
      run(text.trim() || label, () =>
        conversationApi.sendPhotoTurn(photo, language, conversationId.current, text.trim(), profile ?? null),
      ),
    [language, profile, run],
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
    sendPhoto,
    choose,
    rate,
    reset,
  };
}
