/**
 * Document briefs (/officer/documents): an officer uploads a circular, advisory or scheme
 * notification and gets a structured brief from the on-device assistant, plus the fields the
 * rule-based extractor found (authority, validity dates, crops...). The file is read on the
 * KrishiOS server only and is not stored.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, FileText, Loader2, XCircle } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { useDocumentAnalysis } from '@/features/assistant/useDocumentAnalysis';
import { asAnalysisLanguage, type AnalysisLanguage } from '@/services/api/assistant';

// Extracted fields shown to the officer, in this order (others are left out).
const FIELDS = ['authority', 'issued_at', 'valid_from', 'valid_to', 'crops', 'hazards',
  'severity', 'actions'] as const;

const show = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.map(String).join(', ') : '—';
  const text = String(value);
  return /^\d{4}-\d{2}-\d{2}T/.test(text) ? text.slice(0, 10) : text;
};

export const DocumentBriefPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<AnalysisLanguage>(asAnalysisLanguage(i18n.language));
  const [crops, setCrops] = useState('');
  const { phase, ahead, result, analyze, reset, busy } = useDocumentAnalysis();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || busy) return;
    await analyze(file, {
      audience: 'officer',
      language,
      crops: crops.split(',').map((c) => c.trim()).filter(Boolean),
    });
  };

  const fields = (result?.extracted as { fields?: Record<string, { value?: unknown }> } | undefined)
    ?.fields ?? {};

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-heading font-bold text-text">{t('docBrief.title')}</h1>
        <p className="text-small text-text-secondary">{t('docBrief.subtitle')}</p>
      </div>

      <form onSubmit={submit} className="p-4 rounded-xl bg-surface border border-border space-y-3">
        <label htmlFor="brief-file" className="text-small font-semibold text-text block">
          {t('docBrief.file')}
        </label>
        <input
          id="brief-file"
          type="file"
          accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            reset();
          }}
          className="block w-full text-small text-text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-small file:font-medium file:text-primary-700"
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label htmlFor="brief-lang" className="text-caption font-semibold text-text block mb-1">
              {t('docBrief.language')}
            </label>
            <select
              id="brief-lang"
              value={language}
              onChange={(e) => setLanguage(e.target.value as AnalysisLanguage)}
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-small text-text"
            >
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
              <option value="te">తెలుగు</option>
            </select>
          </div>
          <div>
            <label htmlFor="brief-crops" className="text-caption font-semibold text-text block mb-1">
              {t('docBrief.crops')}
            </label>
            <input
              id="brief-crops"
              type="text"
              value={crops}
              onChange={(e) => setCrops(e.target.value)}
              placeholder={t('docBrief.cropsPlaceholder')}
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-small text-text"
            />
          </div>
        </div>
        <p className="text-caption text-text-muted">{t('docBrief.privacy')}</p>
        <Button type="submit" variant="primary" disabled={!file || busy}>
          <FileText className="w-4 h-4 mr-1.5" aria-hidden="true" />
          {busy ? t('docBrief.working') : t('docBrief.submit')}
        </Button>
      </form>

      {busy && (
        <p role="status" className="flex items-center gap-2 text-small text-text-secondary">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          {phase === 'queued' && ahead > 0
            ? t('workspace.docQueued', { count: ahead })
            : t('docBrief.reading')}
        </p>
      )}
      {phase === 'failed' && (
        <p role="alert" className="flex items-center gap-2 text-small text-danger-700">
          <XCircle className="w-4 h-4" aria-hidden="true" />
          {t('workspace.docFailed')}
        </p>
      )}

      {phase === 'done' && result && (
        <section className="space-y-4" aria-live="polite">
          <div className="p-4 rounded-xl bg-surface border border-border space-y-2">
            <h2 className="flex items-center gap-2 text-subheading font-bold text-text">
              <CheckCircle2 className="w-5 h-5 text-success-600" aria-hidden="true" />
              {t('docBrief.brief')}
            </h2>
            <p className="text-small text-text whitespace-pre-line">{result.text}</p>
            <ul className="text-caption text-text-muted space-y-0.5">
              <li>{t('docBrief.read', { read: result.parts_read, total: result.parts_total, pages: result.pages })}</li>
              {result.dropped_lines > 0 && (
                <li>{t('docBrief.dropped', { count: result.dropped_lines })}</li>
              )}
              {result.translation_failed && <li>{t('workspace.docEnglish')}</li>}
            </ul>
          </div>

          <div className="p-4 rounded-xl bg-surface border border-border">
            <h2 className="text-small font-bold text-text mb-2">{t('docBrief.fields')}</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-[10rem_1fr] gap-x-4 gap-y-1 text-small">
              {FIELDS.map((key) => (
                <React.Fragment key={key}>
                  <dt className="text-text-muted">{t(`docBrief.field.${key}`)}</dt>
                  <dd className="text-text">{show(fields[key]?.value)}</dd>
                </React.Fragment>
              ))}
            </dl>
            <p className="text-caption text-text-muted mt-2">{t('docBrief.fieldsNote')}</p>
          </div>
        </section>
      )}
    </div>
  );
};

export default DocumentBriefPage;
