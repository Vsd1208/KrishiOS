/**
 * Officer bulletin editor: review extracted fields against highlighted source spans, target,
 * preview and approve translations, then approve & publish or schedule. Published bulletins
 * are immutable: withdraw or supersede them. Every action is audit-logged server-side.
 */

import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2, History, Languages, Send, X } from 'lucide-react';

import {
  govconnectApi,
  type BulletinDetail,
  type BulletinFields,
  type BulletinTranslation,
  type Lang,
  type Severity,
} from '@/services/api/govconnect';
import { DistrictPicker } from './DistrictPicker';
import { formatDate, highlightSegments, SEVERITY_STYLE } from './format';

const EDITABLE = new Set(['draft', 'needs_review', 'approved', 'scheduled']);
const APPROVABLE = new Set(['draft', 'needs_review']);
const DELIVERABLE = new Set(['passthrough', 'auto_approved', 'approved']);
const LANGS: Lang[] = ['te', 'hi', 'en'];
const SEVERITIES: Severity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const LEVELS = ['national', 'state', 'district', 'block'] as const;
const FIELD_COLOURS: Record<string, string> = {
  authority: 'bg-info-100',
  issued_at: 'bg-purple-100',
  valid_from: 'bg-purple-100',
  valid_to: 'bg-purple-100',
  district_codes: 'bg-emerald-100',
  block_codes: 'bg-emerald-100',
  crops: 'bg-lime-100',
  hazard_type: 'bg-orange-100',
  severity: 'bg-red-100',
  recommended_actions: 'bg-sky-50',
};

const toLocal = (iso: string | null | undefined): string =>
  iso ? new Date(new Date(iso).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16) : '';
const fromLocal = (v: string): string | null => (v ? new Date(v).toISOString() : null);

export interface BulletinEditorProps {
  uuid: string;
  onOpen?: (uuid: string) => void;
  onClose?: () => void;
}

export const BulletinEditor: React.FC<BulletinEditorProps> = ({ uuid, onOpen, onClose }) => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const key = ['govconnect', 'bulletin', uuid];
  const { data: b, isLoading } = useQuery({ queryKey: key, queryFn: () => govconnectApi.get(uuid) });
  const [error, setError] = useState<string | null>(null);
  const done = (next?: BulletinDetail) => {
    setError(null);
    if (next) qc.setQueryData(key, next);
    void qc.invalidateQueries({ queryKey: ['govconnect', 'list'] });
  };
  const fail = (e: unknown) => {
    const message = (e as { message?: unknown })?.message;
    setError(typeof message === 'string' ? message : t('chat.error'));
  };
  const save = useMutation({ mutationFn: (f: BulletinFields) => govconnectApi.edit(uuid, f), onSuccess: done, onError: fail });
  const translate = useMutation({ mutationFn: () => govconnectApi.translate(uuid), onSuccess: done, onError: fail });
  const approveTr = useMutation({
    mutationFn: (p: { lang: Lang; title?: string; body?: string }) =>
      govconnectApi.approveTranslation(uuid, p.lang, { title: p.title, body: p.body }),
    onSuccess: done,
    onError: fail,
  });
  const [publishAt, setPublishAt] = useState('');
  const approve = useMutation({
    mutationFn: () => govconnectApi.approve(uuid, fromLocal(publishAt)),
    onSuccess: (r) => done(r.bulletin),
    onError: fail,
  });
  const [reason, setReason] = useState('');
  const withdraw = useMutation({ mutationFn: () => govconnectApi.withdraw(uuid, reason), onSuccess: done, onError: fail });
  const supersede = useMutation({
    mutationFn: () => govconnectApi.supersede(uuid),
    onSuccess: (n) => {
      done();
      onOpen?.(n.uuid);
    },
    onError: fail,
  });
  const [showAudit, setShowAudit] = useState(false);
  const audit = useQuery({
    queryKey: [...key, 'audit'],
    queryFn: () => govconnectApi.audit(uuid),
    enabled: showAudit,
  });

  if (isLoading || !b) return <p className="text-small text-text-muted">{t('extension.loading')}</p>;
  const editable = EDITABLE.has(b.status);
  const low = new Set(b.extraction.low_confidence ?? []);

  return (
    <article className="rounded-2xl border border-border bg-surface p-4 space-y-4" aria-label={b.title}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-caption">
            <span className="px-2 py-0.5 rounded-full bg-surface-raised font-semibold">{t(`gc.status.${b.status}`)}</span>
            <span className={`px-2 py-0.5 rounded-full font-bold ${SEVERITY_STYLE[b.severity]}`}>
              {t(`govt.severity.${b.severity}`)}
            </span>
            <span className="text-text-muted">
              {t(`gc.source.${b.source_type}`)}
              {b.extraction.extractor ? ` · ${b.extraction.extractor}` : ''}
            </span>
            {b.supersedes && <span className="text-amber-800">{t('gc.supersedesNote')}</span>}
          </div>
          <h2 className="text-body font-bold text-text">{b.title}</h2>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} aria-label={t('gc.close')} className="p-1 cursor-pointer">
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </header>

      {error && (
        <p role="alert" className="flex items-start gap-1.5 rounded-lg bg-danger-50 p-2 text-caption text-danger-700">
          <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      <section className="space-y-1">
        <h3 className="text-small font-bold text-text">{t('gc.sourceText')}</h3>
        <p className="text-caption text-text-muted">{t('gc.provenanceHelp')}</p>
        <div className="max-h-64 overflow-y-auto rounded-lg border border-border bg-surface-raised p-3 text-small whitespace-pre-wrap" lang={b.original_language}>
          {highlightSegments(b.body, b.provenance).map((seg, i) =>
            seg.field ? (
              <mark key={i} title={t(`gc.fields.${seg.field}`)} className={`${FIELD_COLOURS[seg.field] ?? 'bg-yellow-100'} rounded px-0.5`}>
                {seg.text}
              </mark>
            ) : (
              <span key={i}>{seg.text}</span>
            ),
          )}
        </div>
      </section>

      <FieldsForm b={b} low={low} disabled={!editable || save.isPending} onSave={(f) => save.mutate(f)} />

      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-small font-bold text-text flex items-center gap-1.5">
            <Languages className="w-4 h-4" aria-hidden="true" />
            {t('gc.translations')}
          </h3>
          {editable && (
            <button
              type="button"
              onClick={() => translate.mutate()}
              disabled={translate.isPending}
              className="px-3 py-1.5 rounded-lg border border-border text-caption font-semibold cursor-pointer disabled:opacity-50"
            >
              {translate.isPending ? t('gc.translating') : t('gc.generateTranslations')}
            </button>
          )}
        </div>
        {b.translations.length === 0 && <p className="text-caption text-text-muted">{t('gc.noTranslations')}</p>}
        {b.translations.map((tr) => (
          <TranslationRow
            key={tr.language}
            b={b}
            tr={tr}
            disabled={!editable || approveTr.isPending}
            onApprove={(edited) => approveTr.mutate({ lang: tr.language, ...edited })}
          />
        ))}
      </section>

      {APPROVABLE.has(b.status) && (
        <section className="space-y-2 rounded-xl border border-border p-3">
          <h3 className="text-small font-bold text-text">{t('gc.publish')}</h3>
          {b.readiness.length > 0 ? (
            <ul className="list-disc pl-5 text-caption text-danger-700">
              {b.readiness.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          ) : (
            <p className="flex items-center gap-1 text-caption text-success-700">
              <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
              {t('gc.ready')}
            </p>
          )}
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-caption text-text-secondary">
              {t('gc.scheduleFor')}
              <input
                type="datetime-local"
                value={publishAt}
                onChange={(e) => setPublishAt(e.target.value)}
                className="block mt-1 rounded-lg border border-border bg-surface px-2 py-1 text-small"
              />
            </label>
            <button
              type="button"
              disabled={b.readiness.length > 0 || approve.isPending}
              onClick={() => approve.mutate()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
              {publishAt ? t('gc.approveSchedule') : t('gc.approvePublish')}
            </button>
          </div>
        </section>
      )}

      {(b.status === 'published' || b.status === 'scheduled' || b.status === 'approved') && (
        <section className="space-y-2 rounded-xl border border-border p-3">
          <h3 className="text-small font-bold text-text">{t('gc.afterPublish')}</h3>
          {b.published_at && (
            <p className="text-caption text-text-muted">
              {t('gc.publishedAt', { when: formatDate(b.published_at, 'en') })} · {t('gc.index')}: {b.index_state ?? '—'}
            </p>
          )}
          {b.status === 'scheduled' && (
            <p className="text-caption text-text-muted">{t('gc.scheduledAt', { when: formatDate(b.publish_at, 'en') })}</p>
          )}
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-caption text-text-secondary flex-1 min-w-[200px]">
              {t('gc.withdrawReason')}
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small"
              />
            </label>
            <button
              type="button"
              disabled={reason.trim().length < 3 || withdraw.isPending}
              onClick={() => withdraw.mutate()}
              className="px-3 py-1.5 rounded-lg border border-danger-400 text-danger-700 text-small font-semibold cursor-pointer disabled:opacity-50"
            >
              {t('gc.withdraw')}
            </button>
            {b.status === 'published' && (
              <button
                type="button"
                disabled={supersede.isPending}
                onClick={() => supersede.mutate()}
                className="px-3 py-1.5 rounded-lg border border-border text-small font-semibold cursor-pointer disabled:opacity-50"
              >
                {t('gc.supersede')}
              </button>
            )}
          </div>
        </section>
      )}
      {b.withdrawn_reason && <p className="text-caption text-danger-700">{t('govt.withdrawnReason', { reason: b.withdrawn_reason })}</p>}

      <section>
        <button
          type="button"
          onClick={() => setShowAudit((v) => !v)}
          aria-expanded={showAudit}
          className="flex items-center gap-1 text-caption font-semibold text-text-secondary cursor-pointer"
        >
          <History className="w-4 h-4" aria-hidden="true" />
          {t('gc.audit')}
        </button>
        {showAudit && (
          <ol className="mt-2 space-y-1 text-caption">
            {(audit.data ?? []).map((a, i) => (
              <li key={i} className="flex flex-wrap gap-2">
                <span className="text-text-muted">{formatDate(a.at, 'en')}</span>
                <strong>{a.action}</strong>
                <code className="text-text-secondary">{JSON.stringify(a.detail)}</code>
              </li>
            ))}
          </ol>
        )}
      </section>
    </article>
  );
};

const FieldsForm: React.FC<{
  b: BulletinDetail;
  low: Set<string>;
  disabled: boolean;
  onSave: (f: BulletinFields) => void;
}> = ({ b, low, disabled, onSave }) => {
  const { t } = useTranslation();
  const initial = useMemo(
    () => ({
      title: b.title,
      authority: b.authority,
      authority_level: b.authority_level,
      severity: b.severity,
      hazard_type: b.hazard_type ?? '',
      valid_from: toLocal(b.valid_from),
      valid_to: toLocal(b.valid_to),
      district_codes: b.district_codes,
      crops: b.crops.join(', '),
      target_languages: b.target_languages,
      max_acres: b.segment?.max_acres?.toString() ?? '',
    }),
    [b],
  );
  const [f, setF] = useState(initial);
  const lowMark = (field: string) =>
    low.has(field) ? <span className="ml-1 text-amber-700" title={t('gc.lowConfidence')}>⚠</span> : null;
  const input = 'block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small';

  return (
    <form
      className="grid gap-3 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        onSave({
          title: f.title,
          authority: f.authority,
          authority_level: f.authority_level,
          severity: f.severity,
          hazard_type: f.hazard_type || null,
          valid_from: fromLocal(f.valid_from),
          valid_to: fromLocal(f.valid_to),
          district_codes: f.district_codes,
          crops: f.crops.split(',').map((c) => c.trim()).filter(Boolean),
          target_languages: f.target_languages,
          segment: f.max_acres ? { max_acres: Number(f.max_acres) } : {},
        });
      }}
    >
      <label className="text-caption text-text-secondary sm:col-span-2">
        {t('gc.fields.title')}
        <input value={f.title} disabled={disabled} onChange={(e) => setF({ ...f, title: e.target.value })} className={input} />
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.authority')}
        {lowMark('authority')}
        <input value={f.authority} disabled={disabled} onChange={(e) => setF({ ...f, authority: e.target.value })} className={input} />
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.authority_level')}
        <select value={f.authority_level} disabled={disabled} onChange={(e) => setF({ ...f, authority_level: e.target.value as BulletinDetail['authority_level'] })} className={input}>
          {LEVELS.map((l) => (
            <option key={l} value={l}>
              {t(`gc.levels.${l}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.severity')}
        {lowMark('severity')}
        <select value={f.severity} disabled={disabled} onChange={(e) => setF({ ...f, severity: e.target.value as Severity })} className={input}>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {t(`govt.severity.${s}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.hazard_type')}
        {lowMark('hazard_type')}
        <input value={f.hazard_type} disabled={disabled} onChange={(e) => setF({ ...f, hazard_type: e.target.value })} className={input} />
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.valid_from')}
        {lowMark('valid_from')}
        <input type="datetime-local" value={f.valid_from} disabled={disabled} onChange={(e) => setF({ ...f, valid_from: e.target.value })} className={input} />
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.valid_to')}
        {lowMark('valid_to')}
        <input type="datetime-local" value={f.valid_to} disabled={disabled} onChange={(e) => setF({ ...f, valid_to: e.target.value })} className={input} />
      </label>
      <div className="sm:col-span-2 space-y-1">
        <p className="text-caption text-text-secondary">
          {t('gc.fields.district_codes')}
          {lowMark('district_codes')}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {f.district_codes.map((code) => (
            <span key={code} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-caption">
              LGD {code}
              {!disabled && (
                <button
                  type="button"
                  aria-label={t('places.remove')}
                  onClick={() => setF({ ...f, district_codes: f.district_codes.filter((c) => c !== code) })}
                  className="cursor-pointer"
                >
                  <X className="w-3 h-3" aria-hidden="true" />
                </button>
              )}
            </span>
          ))}
        </div>
        {!disabled && (
          <DistrictPicker
            label={t('gc.addDistrict')}
            onPick={(d) =>
              setF({ ...f, district_codes: Array.from(new Set([...f.district_codes, d.lgd_district_code])) })
            }
          />
        )}
      </div>
      <label className="text-caption text-text-secondary">
        {t('gc.fields.crops')}
        {lowMark('crops')}
        <input value={f.crops} disabled={disabled} onChange={(e) => setF({ ...f, crops: e.target.value })} placeholder="paddy, cotton" className={input} />
      </label>
      <label className="text-caption text-text-secondary">
        {t('gc.maxAcres')}
        <input type="number" min={0} value={f.max_acres} disabled={disabled} onChange={(e) => setF({ ...f, max_acres: e.target.value })} className={input} />
      </label>
      <fieldset className="sm:col-span-2 text-caption text-text-secondary">
        <legend>{t('gc.fields.target_languages')}</legend>
        <div className="flex gap-3 pt-1">
          {LANGS.map((l) => (
            <label key={l} className="flex items-center gap-1">
              <input
                type="checkbox"
                disabled={disabled}
                checked={f.target_languages.includes(l)}
                onChange={(e) =>
                  setF({
                    ...f,
                    target_languages: e.target.checked
                      ? [...f.target_languages, l]
                      : f.target_languages.filter((x) => x !== l),
                  })
                }
              />
              {l}
            </label>
          ))}
        </div>
      </fieldset>
      {!disabled && (
        <button type="submit" className="sm:col-span-2 justify-self-start px-4 py-2 rounded-lg border border-primary-600 text-primary-700 text-small font-semibold cursor-pointer">
          {t('gc.save')}
        </button>
      )}
    </form>
  );
};

const TranslationRow: React.FC<{
  b: BulletinDetail;
  tr: BulletinTranslation;
  disabled: boolean;
  onApprove: (edited: { title?: string; body?: string }) => void;
}> = ({ b, tr, disabled, onApprove }) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState(tr.title);
  const [body, setBody] = useState(tr.body);
  const ok = DELIVERABLE.has(tr.status);
  const edited = title !== tr.title || body !== tr.body;
  return (
    <div className="rounded-xl border border-border p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-caption">
        <strong className="uppercase">{tr.language}</strong>
        <span className={`px-2 py-0.5 rounded-full font-semibold ${ok ? 'bg-success-50 text-success-700' : 'bg-amber-50 text-amber-800'}`}>
          {t(`gc.trStatus.${tr.status}`)}
        </span>
        {tr.provider && <span className="text-text-muted">{tr.provider}</span>}
      </div>
      {tr.check_issues.length > 0 && (
        <ul className="list-disc pl-5 text-caption text-danger-700">
          {tr.check_issues.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
      {tr.language !== b.original_language && (
        <div className="grid gap-2 md:grid-cols-2">
          <div className="text-caption">
            <p className="font-semibold text-text-secondary">{t('gc.original')}</p>
            <p className="whitespace-pre-wrap text-text" lang={b.original_language}>{b.body}</p>
          </div>
          <div className="text-caption space-y-1">
            <p className="font-semibold text-text-secondary">{t('gc.translation')}</p>
            <input aria-label={`${tr.language} ${t('gc.fields.title')}`} value={title} disabled={disabled} onChange={(e) => setTitle(e.target.value)} lang={tr.language} className="w-full rounded-lg border border-border bg-surface px-2 py-1" />
            <textarea aria-label={`${tr.language} ${t('gc.translation')}`} value={body} disabled={disabled} onChange={(e) => setBody(e.target.value)} rows={5} lang={tr.language} className="w-full rounded-lg border border-border bg-surface px-2 py-1" />
            {tr.back_translation && (
              <p className="text-text-muted">
                <span className="font-semibold">{t('gc.backTranslation')}:</span> {tr.back_translation}
              </p>
            )}
          </div>
        </div>
      )}
      {tr.language !== b.original_language && (tr.status !== 'approved' || edited) && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onApprove(edited ? { title, body } : {})}
          className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-caption font-semibold cursor-pointer disabled:opacity-50"
        >
          {edited ? t('gc.approveEdited') : t('gc.approveTranslation')}
        </button>
      )}
    </div>
  );
};
