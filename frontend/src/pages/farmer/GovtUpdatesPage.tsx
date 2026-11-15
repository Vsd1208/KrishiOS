/**
 * Govt Updates inbox (Phase 4): official bulletins in the farmer's language.
 *
 * Official content is styled apart from AI advice (landmark badge, authority, issue date and
 * validity on every card). Translations are labelled and the official original is one tap
 * away. Actions: listen (TTS), ask about this (opens the chat with the bulletin as context),
 * acknowledge, and flag ("doesn't apply to me" / "unclear") for the officer.
 */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { CheckCircle2, Flag, Landmark, MessageCircleQuestion, PlayCircle } from 'lucide-react';

import { conversationApi } from '@/services/api/conversation';
import { formatDate, SEVERITY_STYLE } from '@/features/govconnect/format';
import { govconnectApi, type FlagReason, type InboxItem } from '@/services/api/govconnect';

const KEY = ['govconnect', 'inbox'] as const;
const FLAG_REASONS: FlagReason[] = ['not_applicable', 'unclear', 'wrong_location', 'other'];
export const GovtUpdatesPage: React.FC = () => {
  const { t } = useTranslation();
  const [showAll, setShowAll] = useState(false);
  const { data = [], isLoading, isError } = useQuery({
    queryKey: [...KEY, showAll],
    queryFn: () => govconnectApi.inbox(!showAll),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-heading font-bold text-text flex items-center gap-2">
          <Landmark className="w-5 h-5 text-info-700" aria-hidden="true" />
          {t('govt.title')}
        </h1>
        <label className="flex items-center gap-1.5 text-caption text-text-secondary cursor-pointer">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          {t('govt.showPast')}
        </label>
      </div>
      <p className="text-caption text-text-muted">{t('govt.officialNote')}</p>
      <Link to="/farmer/help" className="inline-block text-caption text-info-700 underline">
        {t('govt.helpLink')}
      </Link>
      {isLoading && <p className="text-small text-text-muted">{t('extension.loading')}</p>}
      {isError && (
        <p role="alert" className="text-small text-danger-700">
          {t('chat.error')}
        </p>
      )}
      {!isLoading && data.length === 0 && (
        <p className="text-small text-text-muted">{t('govt.empty')}</p>
      )}
      <ul className="space-y-3">
        {data.map((item) => (
          <BulletinCard key={item.bulletin_uuid} item={item} />
        ))}
      </ul>
    </div>
  );
};

const BulletinCard: React.FC<{ item: InboxItem }> = ({ item }) => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showOriginal, setShowOriginal] = useState(false);
  const [flagging, setFlagging] = useState(false);
  const [audio, setAudio] = useState<string | null>(null);
  const [audioError, setAudioError] = useState(false);
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });
  const ack = useMutation({ mutationFn: () => govconnectApi.acknowledge(item.bulletin_uuid), onSuccess: refresh });
  const flag = useMutation({
    mutationFn: (reason: FlagReason) => govconnectApi.flag(item.bulletin_uuid, reason),
    onSuccess: () => {
      setFlagging(false);
      void refresh();
    },
  });
  const listen = useMutation({
    mutationFn: async () => {
      const { audio_uuid } = await govconnectApi.listen(item.bulletin_uuid);
      return URL.createObjectURL(await conversationApi.fetchAudio(audio_uuid));
    },
    onSuccess: setAudio,
    onError: () => setAudioError(true),
  });
  const inactive = item.state !== 'active';
  const lang = i18n.language;

  return (
    <li
      className={`rounded-2xl border-2 bg-surface p-4 space-y-2 ${
        inactive ? 'border-border opacity-75' : 'border-info-200'
      }`}
      lang={showOriginal ? item.original_language : item.language}
    >
      <div className="flex flex-wrap items-center gap-2 text-caption">
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-info-50 text-info-700 font-semibold">
          <Landmark className="w-3.5 h-3.5" aria-hidden="true" />
          {t('govt.official')}
        </span>
        <span className={`px-2 py-0.5 rounded-full font-bold ${SEVERITY_STYLE[item.severity]}`}>
          {t(`govt.severity.${item.severity}`)}
        </span>
        {inactive && (
          <span className="px-2 py-0.5 rounded-full bg-surface-raised text-text-secondary font-semibold">
            {t(`govt.state.${item.state}`)}
          </span>
        )}
      </div>
      <h2 className="text-body font-bold text-text">
        {showOriginal ? item.original_title : item.title}
      </h2>
      <p className="text-caption text-text-secondary">
        {t('govt.issuedBy', { authority: item.authority })} · {t('govt.issued')}{' '}
        {formatDate(item.issued_at, lang)} · {t('govt.validUntil')} {formatDate(item.valid_to, lang)}
      </p>
      <p className="text-small text-text whitespace-pre-line">
        {showOriginal ? item.original_body : item.body}
      </p>
      {item.state === 'withdrawn' && item.withdrawn_reason && (
        <p className="text-caption text-danger-700">
          {t('govt.withdrawnReason', { reason: item.withdrawn_reason })}
        </p>
      )}
      {item.state === 'superseded' && (
        <p className="text-caption text-amber-800">{t('govt.supersededNote')}</p>
      )}
      {item.translated && (
        <button
          type="button"
          onClick={() => setShowOriginal((v) => !v)}
          className="text-caption text-info-700 underline cursor-pointer"
        >
          {showOriginal ? t('govt.showTranslation') : t('govt.showOriginal')}
        </button>
      )}
      {item.translated && !showOriginal && (
        <p className="text-caption text-text-muted">{t('govt.translatedNote')}</p>
      )}
      {item.source_url && (
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-caption text-info-700 underline"
        >
          {t('govt.source')}
        </a>
      )}
      {audio && <audio controls autoPlay src={audio} className="h-8 w-full" />}
      {audioError && <p className="text-caption text-text-muted">{t('govt.audioUnavailable')}</p>}
      <div className="flex flex-wrap gap-2 pt-1">
        <button
          type="button"
          disabled={listen.isPending}
          onClick={() => listen.mutate()}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-small cursor-pointer disabled:opacity-50"
        >
          <PlayCircle className="w-4 h-4" aria-hidden="true" />
          {t('chat.listen')}
        </button>
        {!inactive && (
          <button
            type="button"
            onClick={() =>
              navigate(`/farmer/ask?bulletin=${item.bulletin_uuid}`, {
                state: { bulletinTitle: item.title },
              })
            }
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-small cursor-pointer"
          >
            <MessageCircleQuestion className="w-4 h-4" aria-hidden="true" />
            {t('govt.askAboutThis')}
          </button>
        )}
        {item.acknowledged_at ? (
          <span className="flex items-center gap-1 px-3 py-1.5 text-small text-success-700">
            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
            {t('govt.acknowledged')}
          </span>
        ) : (
          !inactive && (
            <button
              type="button"
              disabled={ack.isPending}
              onClick={() => ack.mutate()}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-info-700 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
              {t('govt.acknowledge')}
            </button>
          )
        )}
        {item.flag_reason ? (
          <span className="px-3 py-1.5 text-caption text-text-muted">{t('govt.flagged')}</span>
        ) : (
          <button
            type="button"
            onClick={() => setFlagging((v) => !v)}
            aria-expanded={flagging}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-small cursor-pointer"
          >
            <Flag className="w-4 h-4" aria-hidden="true" />
            {t('govt.flag')}
          </button>
        )}
      </div>
      {flagging && (
        <div className="flex flex-wrap gap-2" role="group" aria-label={t('govt.flag')}>
          {FLAG_REASONS.map((r) => (
            <button
              key={r}
              type="button"
              disabled={flag.isPending}
              onClick={() => flag.mutate(r)}
              className="px-2.5 py-1 rounded-full border border-border text-caption cursor-pointer"
            >
              {t(`govt.flagReasons.${r}`)}
            </button>
          ))}
        </div>
      )}
    </li>
  );
};

export default GovtUpdatesPage;
