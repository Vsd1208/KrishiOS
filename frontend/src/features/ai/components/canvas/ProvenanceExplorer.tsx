/**
 * ProvenanceExplorer: the sources retrieved for this answer and the answer checks the backend
 * actually reported. Nothing is filled in when data is missing: no sample citations, no default
 * scores and no badges the backend did not award.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, CheckCircle2, AlertCircle, FileQuestion } from 'lucide-react';
import type { Citation } from '@/types/proactive';

interface ProvenanceExplorerProps {
  citations?: Citation[];
  evaluation?: Record<string, unknown>;
}

const num = (e: Record<string, unknown>, ...keys: string[]): number | undefined => {
  for (const k of keys) if (typeof e[k] === 'number') return e[k] as number;
  return undefined;
};

const bool = (e: Record<string, unknown>, ...keys: string[]): boolean | undefined => {
  for (const k of keys) if (typeof e[k] === 'boolean') return e[k] as boolean;
  return undefined;
};

export const ProvenanceExplorer: React.FC<ProvenanceExplorerProps> = ({ citations = [], evaluation = {} }) => {
  const { t } = useTranslation();
  const grounding = num(evaluation, 'groundingRatio', 'grounding_ratio');
  const coherence = num(evaluation, 'coherenceScore', 'coherence_score');
  const hallucination = bool(evaluation, 'hallucinationDetected', 'hallucination_detected');
  const policy = bool(evaluation, 'policyCompliant', 'policy_compliant');
  const passed = t('canvas.sources.passed');
  const flagged = t('canvas.sources.flagged');

  const checks: { label: string; value: string; ok: boolean }[] = [];
  if (grounding !== undefined) {
    checks.push({ label: t('canvas.sources.grounding'), value: `${Math.round(grounding * 100)}%`, ok: grounding >= 0.7 });
  }
  if (coherence !== undefined) {
    checks.push({ label: t('canvas.sources.coherence'), value: `${Math.round(coherence * 100)}%`, ok: coherence >= 0.7 });
  }
  if (hallucination !== undefined) {
    checks.push({ label: t('canvas.sources.hallucination'), value: hallucination ? flagged : passed, ok: !hallucination });
  }
  if (policy !== undefined) {
    checks.push({ label: t('canvas.sources.policy'), value: policy ? passed : flagged, ok: policy });
  }

  return (
    <div className="space-y-4 animate-fadeIn">
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-primary-100 text-primary-700">
          <BookOpen className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-small font-bold text-text">{t('canvas.sources.title')}</h4>
          <p className="text-caption text-text-muted">{t('canvas.sources.subtitle')}</p>
        </div>
      </div>

      {checks.length > 0 && (
        <div className="p-3.5 rounded-xl bg-surface border border-border space-y-2.5">
          <span className="text-caption font-bold text-text-secondary uppercase block">
            {t('canvas.sources.checks')}
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            {checks.map((c) => (
              <div key={c.label} className="p-2 rounded-lg bg-surface-raised border border-border">
                <span className="text-[11px] text-text-muted block">{c.label}</span>
                <span
                  className={`text-small font-extrabold tabular-nums flex items-center justify-center gap-1 ${
                    c.ok ? 'text-success-700' : 'text-danger-700'
                  }`}
                >
                  {c.ok ? (
                    <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
                  )}
                  {c.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {citations.length === 0 ? (
        <div
          className="p-6 rounded-xl border border-dashed border-border bg-surface-raised text-center space-y-2"
          data-testid="no-sources"
        >
          <FileQuestion className="w-8 h-8 text-text-muted mx-auto opacity-60" aria-hidden="true" />
          <p className="text-small text-text-secondary font-medium">{t('canvas.sources.none')}</p>
          <p className="text-caption text-text-muted max-w-sm mx-auto">{t('canvas.sources.noneHelp')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {citations.map((cit, idx) => (
            <div key={cit.citation_id || idx} className="p-3.5 rounded-xl bg-surface border border-border space-y-2 shadow-xs">
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-0.5 min-w-0">
                  <h5 className="text-small font-bold text-text leading-snug break-words">{cit.source_title}</h5>
                  {(cit.authority || cit.page) && (
                    <p className="text-caption text-primary-800 font-medium">
                      {cit.authority}
                      {cit.authority && cit.page ? ' · ' : ''}
                      {cit.page ? t('canvas.sources.page', { page: cit.page }) : ''}
                    </p>
                  )}
                </div>
                {typeof cit.relevance_score === 'number' && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-primary-50 text-primary-700 border border-primary-200 shrink-0">
                    {t('canvas.sources.match', { pct: Math.round(cit.relevance_score * 100) })}
                  </span>
                )}
              </div>
              {cit.snippet && (
                <blockquote className="p-2.5 rounded-lg bg-surface-raised border-l-2 border-l-primary-600 text-caption text-text-secondary italic leading-relaxed">
                  &ldquo;{cit.snippet}&rdquo;
                </blockquote>
              )}
              {(cit.document_type || cit.date) && (
                <p className="text-[11px] text-text-muted capitalize">
                  {[cit.document_type, cit.date].filter(Boolean).join(' · ')}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProvenanceExplorer;
