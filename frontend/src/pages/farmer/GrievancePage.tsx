/**
 * Help page (F4): raise and follow grievance tickets, and check scheme eligibility.
 * Eligibility is guidance only; personal status is a link to the official portal.
 */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ExternalLink, LifeBuoy, ScrollText } from 'lucide-react';

import { formatDate } from '@/features/govconnect/format';
import { StatusChip } from '@/features/grievance/StatusChip';
import type { Lang } from '@/services/api/govconnect';
import {
  GRIEVANCE_CATEGORIES,
  grievanceApi,
  schemesApi,
  type EligibilityResult,
  type GrievanceCategory,
  type Scheme,
} from '@/services/api/grievance';

const KEY = ['grievances', 'mine'] as const;
const asLang = (l: string): Lang => (['en', 'hi', 'te'].includes(l) ? (l as Lang) : 'en');
const text = (v: string | Record<string, string>, lang: string): string =>
  typeof v === 'string' ? v : v[lang] || v.en || '';

export const GrievancePage: React.FC = () => {
  const { t } = useTranslation();
  const [tab, setTab] = useState<'tickets' | 'schemes'>('tickets');
  return (
    <div className="space-y-4">
      <h1 className="text-heading font-bold text-text">{t('help.title')}</h1>
      <div role="tablist" className="flex gap-1">
        {(['tickets', 'schemes'] as const).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-small font-semibold border cursor-pointer ${
              tab === k ? 'bg-primary-600 text-white border-primary-600' : 'border-border text-text'
            }`}
          >
            {k === 'tickets' ? (
              <LifeBuoy className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ScrollText className="w-4 h-4" aria-hidden="true" />
            )}
            {t(`help.tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab === 'tickets' ? <Tickets /> : <Schemes />}
    </div>
  );
};

const Tickets: React.FC = () => {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [category, setCategory] = useState<GrievanceCategory>('payment');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  const { data = [] } = useQuery({ queryKey: KEY, queryFn: grievanceApi.mine });
  const raise = useMutation({
    mutationFn: () =>
      grievanceApi.raise({ category, subject, description, language: asLang(i18n.language) }),
    onSuccess: () => {
      setSubject('');
      setDescription('');
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <form
        className="rounded-2xl border border-border bg-surface p-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          raise.mutate();
        }}
      >
        <h2 className="text-body font-bold text-text">{t('help.raise')}</h2>
        <label className="block text-caption text-text-secondary">
          {t('help.category')}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as GrievanceCategory)}
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          >
            {GRIEVANCE_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`help.categories.${c}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-caption text-text-secondary">
          {t('help.subject')}
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            minLength={3}
            required
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          />
        </label>
        <label className="block text-caption text-text-secondary">
          {t('help.description')}
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            minLength={5}
            required
            rows={4}
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          />
        </label>
        <p className="text-caption text-text-muted">{t('help.privacy')}</p>
        <button
          type="submit"
          disabled={raise.isPending}
          className="px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
        >
          {t('help.submit')}
        </button>
        {raise.isError && (
          <p role="alert" className="text-caption text-danger-700">
            {t('chat.error')}
          </p>
        )}
      </form>

      <section className="space-y-2">
        <h2 className="text-body font-bold text-text">{t('help.myTickets')}</h2>
        {data.length === 0 && <p className="text-small text-text-muted">{t('help.noTickets')}</p>}
        <ul className="space-y-2">
          {data.map((tk) => (
            <li key={tk.uuid} className="rounded-xl border border-border bg-surface p-3">
              <button
                type="button"
                onClick={() => setOpen(open === tk.uuid ? null : tk.uuid)}
                aria-expanded={open === tk.uuid}
                className="w-full text-left cursor-pointer"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-text">{tk.subject}</span>
                  <StatusChip ticket={tk} />
                </div>
                <p className="text-caption text-text-muted">
                  {t(`help.categories.${tk.category}`)} · {t('help.due')}{' '}
                  {formatDate(tk.sla_due_at, i18n.language)}
                </p>
              </button>
              {open === tk.uuid && <TicketDetail uuid={tk.uuid} />}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

const TicketDetail: React.FC<{ uuid: string }> = ({ uuid }) => {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['grievances', uuid], queryFn: () => grievanceApi.myTicket(uuid) });
  const act = useMutation({
    mutationFn: (action: 'close' | 'reopen') => grievanceApi.farmerAction(uuid, action),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['grievances'] });
    },
  });
  if (!data) return null;
  return (
    <div className="pt-2 space-y-2">
      <p className="text-small text-text whitespace-pre-line">{data.description}</p>
      <ol className="border-l-2 border-border pl-3 space-y-1">
        {(data.events ?? []).map((e, i) => (
          <li key={i} className="text-caption">
            <span className="text-text-muted">{formatDate(e.at, i18n.language)}</span>{' '}
            {e.status && <strong>{t(`help.status.${e.status}`)}</strong>}
            {e.note && <span className="block text-text">{e.note}</span>}
          </li>
        ))}
      </ol>
      {(data.status === 'resolved' || data.status === 'rejected') && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => act.mutate('close')}
            className="px-3 py-1.5 rounded-lg bg-success-600 text-white text-caption font-semibold cursor-pointer"
          >
            {t('help.confirmResolved')}
          </button>
          <button
            type="button"
            onClick={() => act.mutate('reopen')}
            className="px-3 py-1.5 rounded-lg border border-border text-caption cursor-pointer"
          >
            {t('help.reopen')}
          </button>
        </div>
      )}
    </div>
  );
};

const Schemes: React.FC = () => {
  const { t, i18n } = useTranslation();
  const lang = asLang(i18n.language);
  const { data = [], isLoading } = useQuery({
    queryKey: ['schemes', lang],
    queryFn: () => schemesApi.list(lang),
  });
  const [selected, setSelected] = useState<Scheme | null>(null);
  if (isLoading) return <p className="text-small text-text-muted">{t('extension.loading')}</p>;
  if (data.length === 0) return <p className="text-small text-text-muted">{t('help.noSchemes')}</p>;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ul className="space-y-2">
        {data.map((s) => (
          <li key={s.key}>
            <button
              type="button"
              onClick={() => setSelected(s)}
              aria-pressed={selected?.key === s.key}
              className="w-full text-left rounded-xl border border-border bg-surface p-3 hover:border-primary-400 cursor-pointer"
            >
              <span className="font-semibold text-text block">{text(s.name, lang)}</span>
              <span className="text-caption text-text-secondary">{text(s.summary, lang)}</span>
            </button>
          </li>
        ))}
      </ul>
      {selected && <EligibilityForm key={selected.key} scheme={selected} lang={lang} />}
    </div>
  );
};

const EligibilityForm: React.FC<{ scheme: Scheme; lang: Lang }> = ({ scheme, lang }) => {
  const { t } = useTranslation();
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const check = useMutation({
    mutationFn: () => schemesApi.eligibility(scheme.key, answers, lang),
    onSuccess: setResult,
  });
  return (
    <section className="rounded-2xl border border-border bg-surface p-4 space-y-3">
      <h2 className="text-body font-bold text-text">{text(scheme.name, lang)}</h2>
      {scheme.benefits && <p className="text-small text-text">{text(scheme.benefits, lang)}</p>}
      <ol className="space-y-2">
        {scheme.questions.map((q) => (
          <li key={q.id} className="text-small">
            <p className="text-text">{text(q.question, lang)}</p>
            {q.type === 'bool' ? (
              <div className="flex gap-2 pt-1" role="radiogroup" aria-label={text(q.question, lang)}>
                {[true, false].map((v) => (
                  <button
                    key={String(v)}
                    type="button"
                    role="radio"
                    aria-checked={answers[q.id] === v}
                    onClick={() => setAnswers({ ...answers, [q.id]: v })}
                    className={`px-3 py-1 rounded-full border text-caption cursor-pointer ${
                      answers[q.id] === v ? 'bg-primary-600 text-white border-primary-600' : 'border-border'
                    }`}
                  >
                    {v ? t('help.yes') : t('help.no')}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type={q.type === 'number' ? 'number' : 'text'}
                aria-label={text(q.question, lang)}
                onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                className="mt-1 rounded-lg border border-border bg-surface px-2 py-1 text-small"
              />
            )}
          </li>
        ))}
      </ol>
      <button
        type="button"
        onClick={() => check.mutate()}
        disabled={check.isPending}
        className="px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
      >
        {t('help.checkEligibility')}
      </button>
      {result && (
        <div role="status" className="rounded-xl bg-surface-raised p-3 space-y-1">
          <p className="font-semibold text-text">{t(`help.result.${result.status}`)}</p>
          <p className="text-caption text-text-muted">{t('help.guidanceOnly')}</p>
          <a
            href={result.status_lookup_url || result.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-caption text-info-700 underline"
          >
            {t('help.officialPortal')}
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </a>
        </div>
      )}
    </section>
  );
};

export default GrievancePage;
