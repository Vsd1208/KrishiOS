/**
 * Bulletins (Phase 4): officer upload of official bulletins (PDF, image via OCR, DOCX, text),
 * the list of ingested and composed items by status, and the review/publish editor.
 */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { Upload } from 'lucide-react';

import { BulletinEditor } from '@/features/govconnect/BulletinEditor';
import { formatDate, SEVERITY_STYLE } from '@/features/govconnect/format';
import { govconnectApi } from '@/services/api/govconnect';

const STATUSES = ['', 'needs_review', 'draft', 'scheduled', 'published', 'withdrawn', 'superseded', 'expired'];

export const BulletinsPage: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const open = params.get('open');
  const setOpen = (uuid: string | null) => setParams(uuid ? { open: uuid } : {});
  const [status, setStatus] = useState('');
  const { data = [], isLoading } = useQuery({
    queryKey: ['govconnect', 'list', status],
    queryFn: () => govconnectApi.list(status || undefined),
  });
  const [file, setFile] = useState<File | null>(null);
  const [authority, setAuthority] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const upload = useMutation({
    mutationFn: () =>
      govconnectApi.upload(file as File, {
        ...(authority ? { authority } : {}),
        ...(sourceUrl ? { source_url: sourceUrl } : {}),
      }),
    onSuccess: (b) => {
      setFile(null);
      void qc.invalidateQueries({ queryKey: ['govconnect', 'list'] });
      setOpen(b.uuid);
    },
  });

  return (
    <div className="space-y-4">
      <h1 className="text-heading font-bold text-text">{t('gc.bulletinsTitle')}</h1>
      <form
        className="rounded-2xl border border-border bg-surface p-4 grid gap-3 md:grid-cols-4 items-end"
        onSubmit={(e) => {
          e.preventDefault();
          if (file) upload.mutate();
        }}
      >
        <label className="text-caption text-text-secondary md:col-span-2">
          {t('gc.uploadFile')}
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp,.docx,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block mt-1 w-full text-small"
          />
        </label>
        <label className="text-caption text-text-secondary">
          {t('gc.fields.authority')}
          <input value={authority} onChange={(e) => setAuthority(e.target.value)} className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small" />
        </label>
        <label className="text-caption text-text-secondary">
          {t('gc.sourceUrl')}
          <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1 text-small" />
        </label>
        <button
          type="submit"
          disabled={!file || upload.isPending}
          className="md:col-span-4 justify-self-start flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
        >
          <Upload className="w-4 h-4" aria-hidden="true" />
          {upload.isPending ? t('gc.extracting') : t('gc.uploadExtract')}
        </button>
        {upload.isError && (
          <p role="alert" className="md:col-span-4 text-caption text-danger-700">
            {(upload.error as Error).message}
          </p>
        )}
      </form>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <section className="space-y-2">
          <label className="text-caption text-text-secondary">
            {t('gc.filterStatus')}
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="ml-2 rounded-lg border border-border bg-surface px-2 py-1 text-small">
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s ? t(`gc.status.${s}`) : t('gc.all')}
                </option>
              ))}
            </select>
          </label>
          {isLoading && <p className="text-small text-text-muted">{t('extension.loading')}</p>}
          {!isLoading && data.length === 0 && <p className="text-small text-text-muted">{t('gc.none')}</p>}
          <ul className="space-y-2">
            {data.map((b) => (
              <li key={b.uuid}>
                <button
                  type="button"
                  onClick={() => setOpen(b.uuid)}
                  aria-current={open === b.uuid}
                  className={`w-full text-left rounded-xl border p-3 cursor-pointer ${open === b.uuid ? 'border-primary-500 bg-primary-50/40' : 'border-border bg-surface'}`}
                >
                  <div className="flex flex-wrap items-center gap-2 text-caption">
                    <span className="px-2 py-0.5 rounded-full bg-surface-raised font-semibold">{t(`gc.status.${b.status}`)}</span>
                    <span className={`px-2 py-0.5 rounded-full font-bold ${SEVERITY_STYLE[b.severity]}`}>{t(`govt.severity.${b.severity}`)}</span>
                    <span className="text-text-muted">{formatDate(b.created_at, 'en')}</span>
                  </div>
                  <p className="font-semibold text-text pt-1">{b.title}</p>
                  <p className="text-caption text-text-muted">{b.authority}</p>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <div>
          {open ? (
            <BulletinEditor key={open} uuid={open} onOpen={setOpen} onClose={() => setOpen(null)} />
          ) : (
            <p className="text-small text-text-muted">{t('gc.pickOne')}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default BulletinsPage;
