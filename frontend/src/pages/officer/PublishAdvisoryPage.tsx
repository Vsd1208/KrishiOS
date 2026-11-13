/**
 * Publish Advisory (Phase 4): compose an official advisory (optionally from a template),
 * then continue in the bulletin editor: target → translation preview → approve / schedule.
 * Templates are empty skeletons; the officer supplies every fact.
 */

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { FilePlus2 } from 'lucide-react';

import { govconnectApi, type Lang, type Severity } from '@/services/api/govconnect';

interface Template {
  id: string;
  hazard: string;
  severity: Severity;
}

const TEMPLATES: Template[] = [
  { id: 'weather', hazard: 'heavy_rain', severity: 'MEDIUM' },
  { id: 'pest', hazard: 'pest_outbreak', severity: 'MEDIUM' },
  { id: 'scheme', hazard: 'advisory', severity: 'LOW' },
  { id: 'general', hazard: 'advisory', severity: 'LOW' },
];

export const PublishAdvisoryPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [template, setTemplate] = useState<Template>(TEMPLATES[0] as Template);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [authority, setAuthority] = useState('');
  const [language, setLanguage] = useState<Lang>('en');
  const create = useMutation({
    mutationFn: () =>
      govconnectApi.compose({
        body,
        title: title || undefined,
        authority: authority || undefined,
        hazard_type: template.hazard,
        severity: template.severity,
        original_language: language,
      }),
    onSuccess: (b) => navigate(`/officer/bulletins?open=${b.uuid}`),
  });

  const pick = (tpl: Template) => {
    setTemplate(tpl);
    if (!body.trim()) setBody(t(`gc.templates.${tpl.id}.body`));
    if (!title.trim()) setTitle(t(`gc.templates.${tpl.id}.title`));
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-heading font-bold text-text">{t('gc.publishTitle')}</h1>
      <p className="text-small text-text-secondary">{t('gc.publishHelp')}</p>
      <div role="group" aria-label={t('gc.template')} className="flex flex-wrap gap-2">
        {TEMPLATES.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            aria-pressed={template.id === tpl.id}
            onClick={() => pick(tpl)}
            className={`px-3 py-1.5 rounded-lg border text-small cursor-pointer ${
              template.id === tpl.id ? 'bg-primary-600 text-white border-primary-600' : 'border-border'
            }`}
          >
            {t(`gc.templates.${tpl.id}.name`)}
          </button>
        ))}
      </div>
      <form
        className="rounded-2xl border border-border bg-surface p-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="block text-caption text-text-secondary">
          {t('gc.fields.title')}
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small" />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-caption text-text-secondary">
            {t('gc.fields.authority')}
            <input value={authority} onChange={(e) => setAuthority(e.target.value)} required className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small" />
          </label>
          <label className="block text-caption text-text-secondary">
            {t('gc.writtenIn')}
            <select value={language} onChange={(e) => setLanguage(e.target.value as Lang)} className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small">
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="te">తెలుగు</option>
            </select>
          </label>
        </div>
        <label className="block text-caption text-text-secondary">
          {t('gc.officialText')}
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
            rows={10}
            lang={language}
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          />
        </label>
        <p className="text-caption text-text-muted">{t('gc.composeNote')}</p>
        <button
          type="submit"
          disabled={!body.trim() || create.isPending}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
        >
          <FilePlus2 className="w-4 h-4" aria-hidden="true" />
          {t('gc.createDraft')}
        </button>
        {create.isError && (
          <p role="alert" className="text-caption text-danger-700">
            {(create.error as Error).message}
          </p>
        )}
      </form>
    </div>
  );
};

export default PublishAdvisoryPage;
