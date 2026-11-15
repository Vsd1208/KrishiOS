/**
 * Assisted mode (F6) for extension workers: my farmers + consent, asking on a farmer's behalf,
 * review-before-share queue, and batch registration (up to 50 farmers, consent per batch).
 */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, MessageSquare, Share2, Trash2, UserPlus, X } from 'lucide-react';

import { FarmerChat } from '@/features/conversation/FarmerChat';
import type { BotLanguage } from '@/services/api/conversation';
import {
  CONSENT_METHODS,
  extensionApi,
  type AssignedFarmer,
  type BatchRow,
  type ConsentMethod,
} from '@/services/api/extension';
import { parseFarmerLines } from '@/features/extension/parseFarmerLines';

type Tab = 'farmers' | 'queue' | 'register';
const KEYS = { farmers: ['extension', 'farmers'], queue: ['extension', 'queue'] } as const;
const asBotLanguage = (l: string): BotLanguage =>
  (['en', 'hi', 'te'] as string[]).includes(l.slice(0, 2)) ? (l.slice(0, 2) as BotLanguage) : 'en';

export const ExtensionPage: React.FC = () => {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>('farmers');
  const [assisting, setAssisting] = useState<AssignedFarmer | null>(null);

  if (assisting) {
    return (
      <div className="flex flex-col h-full min-h-0 gap-2">
        <div className="flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-4 py-2">
          <p className="text-small text-amber-900">
            {t('extension.assistingBanner', { name: assisting.full_name })}
          </p>
          <button
            type="button"
            onClick={() => setAssisting(null)}
            className="flex items-center gap-1 text-caption font-semibold cursor-pointer"
          >
            <X className="w-4 h-4" aria-hidden="true" />
            {t('extension.endSession')}
          </button>
        </div>
        <div className="flex-1 min-h-[480px] rounded-2xl border border-border bg-surface overflow-hidden">
          <FarmerChat
            initialLanguage={asBotLanguage(assisting.preferred_language)}
            actAsFarmerId={assisting.farmer_id}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-heading font-bold text-text">{t('extension.title')}</h1>
      <div role="tablist" className="flex gap-1">
        {(['farmers', 'queue', 'register'] as const).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`px-3 py-1.5 rounded-lg text-small font-semibold border cursor-pointer ${
              tab === k ? 'bg-primary-600 text-white border-primary-600' : 'border-border text-text'
            }`}
          >
            {t(`extension.tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab === 'farmers' && <MyFarmers onAssist={setAssisting} />}
      {tab === 'queue' && <ReviewQueue />}
      {tab === 'register' && <BatchRegister />}
    </div>
  );
};

const MyFarmers: React.FC<{ onAssist: (f: AssignedFarmer) => void }> = ({ onAssist }) => {
  const { t } = useTranslation();
  const { data = [], isLoading, isError } = useQuery({
    queryKey: KEYS.farmers,
    queryFn: extensionApi.myFarmers,
  });
  if (isLoading) return <p className="text-small text-text-muted">{t('extension.loading')}</p>;
  if (isError) return <p role="alert" className="text-small text-danger-700">{t('chat.error')}</p>;
  if (data.length === 0) return <p className="text-small text-text-muted">{t('extension.noFarmers')}</p>;
  return (
    <ul className="space-y-2">
      {data.map((f) => (
        <li key={f.farmer_id} className="rounded-xl border border-border bg-surface p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-semibold text-text">{f.full_name}</p>
              <p className="text-caption text-text-muted">
                {f.village} · {f.preferred_language}
              </p>
            </div>
            <span
              className={`px-2 py-0.5 rounded-full text-caption font-semibold ${
                f.consent_status === 'granted'
                  ? 'bg-success-50 text-success-700'
                  : 'bg-amber-50 text-amber-800'
              }`}
            >
              {t(`extension.consent.${f.consent_status}`)}
            </span>
          </div>
          {f.consent_status === 'granted' ? (
            <button
              type="button"
              onClick={() => onAssist(f)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer"
            >
              <MessageSquare className="w-4 h-4" aria-hidden="true" />
              {t('extension.askForFarmer')}
            </button>
          ) : (
            <ConsentForm farmerId={f.farmer_id} />
          )}
        </li>
      ))}
    </ul>
  );
};

const ConsentForm: React.FC<{ farmerId: number }> = ({ farmerId }) => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [method, setMethod] = useState<ConsentMethod>('verbal_recorded');
  const [evidence, setEvidence] = useState('');
  const save = useMutation({
    mutationFn: () => extensionApi.recordConsent(farmerId, { granted: true, method, evidence: evidence || null }),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.farmers }),
  });
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <label className="text-caption text-text-secondary">
        {t('extension.consentMethod')}
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value as ConsentMethod)}
          className="block mt-1 rounded-lg border border-border bg-surface px-2 py-1 text-small"
        >
          {CONSENT_METHODS.map((m) => (
            <option key={m} value={m}>
              {t(`extension.methods.${m}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-caption text-text-secondary flex-1 min-w-[160px]">
        {t('extension.evidence')}
        <input
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small"
        />
      </label>
      <button
        type="submit"
        disabled={save.isPending}
        className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-primary-600 text-primary-700 text-small font-semibold cursor-pointer disabled:opacity-50"
      >
        <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
        {t('extension.recordConsent')}
      </button>
      {save.isError && <p role="alert" className="w-full text-caption text-danger-700">{t('chat.error')}</p>}
    </form>
  );
};

const ReviewQueue: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({ queryKey: KEYS.queue, queryFn: extensionApi.reviewQueue });
  const decide = useMutation({
    mutationFn: ({ uuid, share }: { uuid: string; share: boolean }) => extensionApi.share(uuid, share),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.queue }),
  });
  if (isLoading) return <p className="text-small text-text-muted">{t('extension.loading')}</p>;
  if (data.length === 0) return <p className="text-small text-text-muted">{t('extension.queueEmpty')}</p>;
  return (
    <ul className="space-y-2">
      {data.map((a) => (
        <li key={a.turn_uuid} className="rounded-xl border border-border bg-surface p-3 space-y-2">
          <p className="text-caption text-text-muted">{t('extension.question')}</p>
          <p className="text-small text-text" lang={a.language}>{a.question}</p>
          <p className="text-caption text-text-muted">{t('extension.answer')}</p>
          <p className="text-small text-text whitespace-pre-line" lang={a.language}>{a.answer}</p>
          {a.answer_en && a.language !== 'en' && (
            <details className="text-caption text-text-secondary">
              <summary className="cursor-pointer">{t('extension.englishVersion')}</summary>
              <p className="whitespace-pre-line pt-1">{a.answer_en}</p>
            </details>
          )}
          {a.requires_review && (
            <p className="text-caption text-amber-800">{t('chat.reviewNotice')}</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={decide.isPending || a.requires_review}
              title={a.requires_review ? t('chat.reviewNotice') : undefined}
              onClick={() => decide.mutate({ uuid: a.turn_uuid, share: true })}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
            >
              <Share2 className="w-4 h-4" aria-hidden="true" />
              {t('extension.share')}
            </button>
            <button
              type="button"
              disabled={decide.isPending}
              onClick={() => decide.mutate({ uuid: a.turn_uuid, share: false })}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-small cursor-pointer disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" aria-hidden="true" />
              {t('extension.discard')}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
};

const BatchRegister: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [text, setText] = useState('');
  const [method, setMethod] = useState<ConsentMethod>('signed_form');
  const [evidence, setEvidence] = useState('');
  const [lineErrors, setLineErrors] = useState<number[]>([]);
  const [rows, setRows] = useState<BatchRow[] | null>(null);
  const submit = useMutation({
    mutationFn: extensionApi.registerBatch,
    onSuccess: (result) => {
      setRows(result);
      void qc.invalidateQueries({ queryKey: KEYS.farmers });
    },
  });

  const onSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    const { farmers, errors } = parseFarmerLines(text, {
      granted: true,
      method,
      evidence: evidence || null,
    });
    setLineErrors(errors);
    setRows(null);
    if (errors.length === 0 && farmers.length > 0 && farmers.length <= 50) submit.mutate(farmers);
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3 max-w-3xl">
      <p className="text-small text-text-secondary">{t('extension.batchHelp')}</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        aria-label={t('extension.tabs.register')}
        placeholder="Lakshmi, 9876543210, te, 509, Kothagudem, 2.5"
        className="w-full rounded-xl border border-border bg-surface p-3 font-mono text-caption"
      />
      <div className="flex flex-wrap gap-3 items-end">
        <label className="text-caption text-text-secondary">
          {t('extension.consentMethod')}
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as ConsentMethod)}
            className="block mt-1 rounded-lg border border-border bg-surface px-2 py-1 text-small"
          >
            {CONSENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {t(`extension.methods.${m}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-caption text-text-secondary flex-1 min-w-[160px]">
          {t('extension.evidence')}
          <input
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small"
          />
        </label>
        <button
          type="submit"
          disabled={submit.isPending || !text.trim()}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
        >
          <UserPlus className="w-4 h-4" aria-hidden="true" />
          {t('extension.register')}
        </button>
      </div>
      {lineErrors.length > 0 && (
        <p role="alert" className="text-caption text-danger-700">
          {t('extension.badLines', { lines: lineErrors.join(', ') })}
        </p>
      )}
      {rows && (
        <ul className="text-caption space-y-0.5">
          {rows.map((r) => (
            <li key={r.phone} className={r.status === 'created' ? 'text-success-700' : 'text-danger-700'}>
              {r.phone}: {t(`extension.rowStatus.${r.status}`)}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
};

export default ExtensionPage;
