/**
 * Multilingual farmer chat (Phase 3): te / hi / en, text or voice, clarification chips,
 * spoken replies, verified how-to videos and answer feedback.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  BookOpen,
  Mic,
  PlayCircle,
  RotateCcw,
  Send,
  Square,
  ThumbsDown,
  ThumbsUp,
  Video,
  Volume2,
} from 'lucide-react';

import {
  conversationApi,
  type BotLanguage,
  type FarmerProfileHint,
  type FeedbackReason,
} from '@/services/api/conversation';
import { useConversation, type ChatMessage } from './useConversation';

const LANGUAGES: { code: BotLanguage; label: string }[] = [
  { code: 'te', label: 'తెలుగు' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'en', label: 'English' },
];

const REASONS: FeedbackReason[] = ['wrong', 'unclear', 'not_applicable', 'translation', 'unsafe'];

export interface FarmerChatProps {
  initialLanguage?: BotLanguage;
  profile?: FarmerProfileHint | null;
  /** Assisted mode (extension worker). Answers wait in the worker's review queue. */
  actAsFarmerId?: number | null;
}

export const FarmerChat: React.FC<FarmerChatProps> = ({ initialLanguage, profile, actAsFarmerId }) => {
  const { t, i18n } = useTranslation();
  const chat = useConversation({ initialLanguage, profile, actAsFarmerId });
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [chat.messages]);

  const switchLanguage = (code: BotLanguage): void => {
    chat.setLanguage(code);
    void i18n.changeLanguage(code);
  };

  const submit = (e: React.FormEvent): void => {
    e.preventDefault();
    const text = draft;
    setDraft('');
    void chat.sendText(text);
  };

  const lastBot = [...chat.messages].reverse().find((m) => m.role === 'bot');
  const pending = lastBot?.result?.status === 'clarification' ? lastBot.result.clarification : null;

  return (
    <section className="flex flex-col h-full min-h-0" aria-label={t('chat.title')}>
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-border">
        <div role="group" aria-label={t('chat.language')} className="flex gap-1">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              lang={l.code}
              aria-pressed={chat.language === l.code}
              onClick={() => switchLanguage(l.code)}
              className={`px-3 py-1.5 rounded-lg text-small font-semibold border cursor-pointer ${
                chat.language === l.code
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-surface text-text border-border hover:border-primary-400'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-caption text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={chat.speak}
              onChange={(e) => chat.setSpeak(e.target.checked)}
            />
            <Volume2 className="w-3.5 h-3.5" aria-hidden="true" />
            {t('chat.speakReplies')}
          </label>
          {chat.messages.length > 0 && (
            <button
              type="button"
              onClick={chat.reset}
              className="flex items-center gap-1 text-caption font-semibold text-text-muted hover:text-text cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
              {t('chat.newConversation')}
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-3" aria-live="polite">
        {chat.messages.length === 0 && (
          <div className="max-w-xl mx-auto text-center py-8 space-y-2">
            <h2 className="text-heading font-bold text-text">{t('chat.welcome')}</h2>
            <p className="text-small text-text-secondary">{t('chat.welcomeHint')}</p>
          </div>
        )}
        {chat.messages.map((m) =>
          m.role === 'user' ? (
            <div key={m.id} className="flex justify-end">
              <p className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary-600 text-white px-3.5 py-2 text-small">
                {m.text}
              </p>
            </div>
          ) : (
            <BotMessage key={m.id} message={m} onRate={chat.rate} />
          ),
        )}
        {chat.busy && <p className="text-caption text-text-muted">{t('chat.thinking')}</p>}
        {chat.error && (
          <p role="alert" className="text-caption text-danger-700">
            {t('chat.error')}
          </p>
        )}
        <div ref={endRef} />
      </div>

      {pending && pending.choices.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2" role="group" aria-label={pending.question}>
          {pending.choices.map((c) => (
            <button
              key={String(c.value)}
              type="button"
              disabled={chat.busy}
              onClick={() => void chat.choose(pending.slot, c)}
              className="px-3 py-1.5 rounded-full border border-primary-300 bg-primary-50 text-small text-primary-900 hover:bg-primary-100 cursor-pointer disabled:opacity-50"
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={submit} className="flex items-center gap-2 px-4 py-3 border-t border-border">
        <VoiceButton disabled={chat.busy} onRecorded={(blob) => void chat.sendVoice(blob)} />
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          lang={chat.language}
          placeholder={t('chat.placeholder')}
          aria-label={t('chat.placeholder')}
          disabled={chat.busy}
          className="flex-1 rounded-xl border border-border bg-surface px-3 py-2 text-small"
        />
        <button
          type="submit"
          disabled={chat.busy || !draft.trim()}
          aria-label={t('chat.send')}
          className="p-2 rounded-xl bg-primary-600 text-white disabled:opacity-50 cursor-pointer"
        >
          <Send className="w-4 h-4" aria-hidden="true" />
        </button>
      </form>
    </section>
  );
};

const BotMessage: React.FC<{
  message: ChatMessage;
  onRate: (id: string, rating: 'up' | 'down', reason?: FeedbackReason) => Promise<void>;
}> = ({ message, onRate }) => {
  const { t } = useTranslation();
  const r = message.result;
  const [askReason, setAskReason] = useState(false);
  const notice =
    r?.translation_status === 'blocked'
      ? t('chat.translationNotice')
      : r?.requires_review
        ? t('chat.reviewNotice')
        : null;

  return (
    <article className="max-w-[90%] rounded-2xl rounded-bl-sm bg-surface-raised border border-border px-3.5 py-2.5 space-y-2">
      <p className="text-small text-text whitespace-pre-line" lang={r?.language}>
        {message.text}
      </p>
      {notice && (
        <p className="flex items-start gap-1.5 text-caption text-amber-800">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
          {notice}
        </p>
      )}
      {r?.audio_uuid && <ReplyAudio audioUuid={r.audio_uuid} />}
      {r && r.citations.length > 0 && (
        <ul className="text-caption text-text-muted space-y-0.5" aria-label={t('ai.citations')}>
          {r.citations.map((c, i) => (
            <li key={i} className="flex items-center gap-1">
              <BookOpen className="w-3 h-3" aria-hidden="true" />
              {c.title ?? c.source ?? t('chat.source')}
            </li>
          ))}
        </ul>
      )}
      {r && r.media.length > 0 && (
        <div className="space-y-1.5">
          {r.media.map((v) => (
            <a
              key={v.uuid}
              href={v.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg border border-border bg-surface p-2 text-caption hover:border-primary-400"
            >
              <Video className="w-4 h-4 text-primary-600 shrink-0" aria-hidden="true" />
              <span className="flex-1">
                <span className="font-semibold text-text block">{v.title}</span>
                <span className="text-text-muted">
                  {t('chat.verifiedVideo')}
                  {v.source_org ? ` · ${v.source_org}` : ''}
                </span>
              </span>
            </a>
          ))}
        </div>
      )}
      {r?.status === 'answered' && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {message.feedback ? (
            <span className="text-caption text-text-muted">{t('chat.thanks')}</span>
          ) : askReason ? (
            REASONS.map((reason) => (
              <button
                key={reason}
                type="button"
                onClick={() => void onRate(message.id, 'down', reason)}
                className="px-2 py-1 rounded-full border border-border text-caption cursor-pointer hover:border-danger-400"
              >
                {t(`chat.reasons.${reason}`)}
              </button>
            ))
          ) : (
            <>
              <button
                type="button"
                aria-label={t('chat.helpful')}
                onClick={() => void onRate(message.id, 'up')}
                className="p-1 text-text-muted hover:text-success-700 cursor-pointer"
              >
                <ThumbsUp className="w-4 h-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={t('chat.notHelpful')}
                onClick={() => setAskReason(true)}
                className="p-1 text-text-muted hover:text-danger-700 cursor-pointer"
              >
                <ThumbsDown className="w-4 h-4" aria-hidden="true" />
              </button>
            </>
          )}
        </div>
      )}
    </article>
  );
};

const ReplyAudio: React.FC<{ audioUuid: string }> = ({ audioUuid }) => {
  const { t } = useTranslation();
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => () => {
    if (src) URL.revokeObjectURL(src);
  }, [src]);

  const load = async (): Promise<void> => {
    try {
      setSrc(URL.createObjectURL(await conversationApi.fetchAudio(audioUuid)));
    } catch {
      setFailed(true);
    }
  };

  if (failed) return null;
  if (src) return <audio controls autoPlay src={src} className="h-8 w-full" />;
  return (
    <button
      type="button"
      onClick={() => void load()}
      className="flex items-center gap-1 text-caption font-semibold text-primary-700 cursor-pointer"
    >
      <PlayCircle className="w-4 h-4" aria-hidden="true" />
      {t('chat.listen')}
    </button>
  );
};

const VoiceButton: React.FC<{ disabled: boolean; onRecorded: (blob: Blob) => void }> = ({
  disabled,
  onRecorded,
}) => {
  const { t } = useTranslation();
  const recorder = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  const start = async (): Promise<void> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        onRecorded(new Blob(chunks, { type: rec.mimeType || 'audio/webm' }));
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch {
      setUnavailable(true);
    }
  };

  const stop = (): void => {
    recorder.current?.stop();
    recorder.current = null;
    setRecording(false);
  };

  if (unavailable || typeof MediaRecorder === 'undefined') return null;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => (recording ? stop() : void start())}
      aria-label={recording ? t('chat.stopRecording') : t('chat.record')}
      aria-pressed={recording}
      className={`p-2 rounded-xl border cursor-pointer disabled:opacity-50 ${
        recording ? 'bg-danger-600 text-white border-danger-600' : 'border-border text-text'
      }`}
    >
      {recording ? <Square className="w-4 h-4" aria-hidden="true" /> : <Mic className="w-4 h-4" aria-hidden="true" />}
    </button>
  );
};

export default FarmerChat;
