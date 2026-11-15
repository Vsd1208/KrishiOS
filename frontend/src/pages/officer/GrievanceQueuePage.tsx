/** Grievance queue (F4) with SLA tracking, and the scheme catalog (drafts → verified). */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ExternalLink } from 'lucide-react';

import { formatDate } from '@/features/govconnect/format';
import { StatusChip } from '@/features/grievance/StatusChip';
import { grievanceApi, schemesApi, type Scheme, type TicketStatus } from '@/services/api/grievance';

const NEXT: Record<string, TicketStatus[]> = {
  open: ['assigned', 'in_progress', 'rejected'],
  assigned: ['in_progress', 'resolved', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  reopened: ['assigned', 'in_progress', 'resolved', 'rejected'],
  resolved: ['closed'],
  rejected: ['closed'],
};

export const GrievanceQueuePage: React.FC = () => {
  const { t } = useTranslation();
  const [tab, setTab] = useState<'queue' | 'schemes'>('queue');
  return (
    <div className="space-y-4">
      <h1 className="text-heading font-bold text-text">{t('gq.title')}</h1>
      <div role="tablist" className="flex gap-1">
        {(['queue', 'schemes'] as const).map((k) => (
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
            {t(`gq.tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab === 'queue' ? <Queue /> : <SchemeCatalog />}
    </div>
  );
};

const Queue: React.FC = () => {
  const { t } = useTranslation();
  const [breachedOnly, setBreachedOnly] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const { data = [] } = useQuery({
    queryKey: ['grievances', 'queue', breachedOnly],
    queryFn: () => grievanceApi.queue({ breachedOnly }),
  });
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="space-y-2">
        <label className="flex items-center gap-1.5 text-caption text-text-secondary cursor-pointer">
          <input type="checkbox" checked={breachedOnly} onChange={(e) => setBreachedOnly(e.target.checked)} />
          {t('gq.breachedOnly')}
        </label>
        {data.length === 0 && <p className="text-small text-text-muted">{t('gq.empty')}</p>}
        <ul className="space-y-2">
          {data.map((tk) => (
            <li key={tk.uuid}>
              <button
                type="button"
                onClick={() => setOpen(tk.uuid)}
                aria-current={open === tk.uuid}
                className={`w-full text-left rounded-xl border p-3 cursor-pointer ${open === tk.uuid ? 'border-primary-500' : 'border-border'} bg-surface`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-text">{tk.subject}</span>
                  <StatusChip ticket={tk} />
                </div>
                <p className="text-caption text-text-muted">
                  {t(`help.categories.${tk.category}`)} · {t('help.due')} {formatDate(tk.sla_due_at, 'en')}
                  {tk.hours_left !== null && ` · ${t('gq.hoursLeft', { h: tk.hours_left })}`}
                </p>
              </button>
            </li>
          ))}
        </ul>
      </section>
      {open && <TicketPanel key={open} uuid={open} />}
    </div>
  );
};

const TicketPanel: React.FC<{ uuid: string }> = ({ uuid }) => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['grievances', 'queue', uuid], queryFn: () => grievanceApi.queueTicket(uuid) });
  const [note, setNote] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const act = useMutation({
    mutationFn: (status: TicketStatus) =>
      grievanceApi.officerAction(uuid, { status, note: note || undefined, public: isPublic }),
    onSuccess: () => {
      setNote('');
      void qc.invalidateQueries({ queryKey: ['grievances'] });
    },
  });
  if (!data) return null;
  return (
    <section className="rounded-2xl border border-border bg-surface p-4 space-y-3">
      <h2 className="text-body font-bold text-text">{data.subject}</h2>
      <p className="text-small whitespace-pre-line" lang={data.language}>{data.description}</p>
      <ol className="border-l-2 border-border pl-3 space-y-1 text-caption">
        {(data.events ?? []).map((e, i) => (
          <li key={i}>
            <span className="text-text-muted">{formatDate(e.at, 'en')}</span>{' '}
            {e.status && <strong>{t(`help.status.${e.status}`)}</strong>} {!e.public && <em>({t('gq.internal')})</em>}
            {e.note && <span className="block">{e.note}</span>}
          </li>
        ))}
      </ol>
      <label className="block text-caption text-text-secondary">
        {t('gq.note')}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small" />
      </label>
      <label className="flex items-center gap-1.5 text-caption text-text-secondary">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
        {t('gq.visibleToFarmer')}
      </label>
      <div className="flex flex-wrap gap-2">
        {(NEXT[data.status] ?? []).map((s) => (
          <button
            key={s}
            type="button"
            disabled={act.isPending}
            onClick={() => act.mutate(s)}
            className="px-3 py-1.5 rounded-lg border border-border text-caption font-semibold cursor-pointer disabled:opacity-50"
          >
            {t(`gq.move.${s}`)}
          </button>
        ))}
      </div>
      {act.isError && (
        <p role="alert" className="text-caption text-danger-700">
          {(act.error as Error).message}
        </p>
      )}
    </section>
  );
};

const SchemeCatalog: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ['schemes', 'admin'], queryFn: () => schemesApi.list('en') });
  const refresh = () => qc.invalidateQueries({ queryKey: ['schemes'] });
  const importDrafts = useMutation({ mutationFn: schemesApi.importDrafts, onSuccess: refresh });
  const verify = useMutation({ mutationFn: schemesApi.verify, onSuccess: refresh });
  const name = (s: Scheme) => (typeof s.name === 'string' ? s.name : s.name.en);
  return (
    <section className="space-y-3">
      <p className="text-small text-text-secondary">{t('gq.schemeHelp')}</p>
      <button
        type="button"
        onClick={() => importDrafts.mutate()}
        className="px-3 py-1.5 rounded-lg border border-border text-small font-semibold cursor-pointer"
      >
        {t('gq.importDrafts')}
      </button>
      <ul className="space-y-2">
        {data.map((s) => (
          <li key={s.key} className="rounded-xl border border-border bg-surface p-3 space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-text">{name(s)}</span>
              <span className={`px-2 py-0.5 rounded-full text-caption font-semibold ${s.status === 'verified' ? 'bg-success-50 text-success-700' : 'bg-amber-50 text-amber-800'}`}>
                {t(`gq.schemeStatus.${s.status}`)}
              </span>
            </div>
            <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-caption text-info-700 underline">
              {s.source_url}
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
            <p className="text-caption text-text-muted">{t('gq.criteriaCount', { n: s.questions.length })}</p>
            {s.status !== 'verified' && (
              <button
                type="button"
                onClick={() => verify.mutate(s.key)}
                className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-caption font-semibold cursor-pointer"
              >
                {t('gq.verify')}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
};

export default GrievanceQueuePage;
