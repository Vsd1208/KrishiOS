/**
 * Farmer feedback dashboard (F13): down-vote rates by language and intent, reasons,
 * triage of flagged answers, and export of regression cases for the evaluation suite.
 */

import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Download } from 'lucide-react';

import {
  feedbackApi,
  type FeedbackBreakdownRow,
  type TriageStatus,
} from '@/services/api/extension';

const KEYS = { summary: ['feedback', 'summary'], list: ['feedback', 'down', 'new'] } as const;

export const FeedbackDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const summary = useQuery({ queryKey: KEYS.summary, queryFn: feedbackApi.summary });
  const flagged = useQuery({
    queryKey: KEYS.list,
    queryFn: () => feedbackApi.list({ rating: 'down', status: 'new' }),
  });
  const triage = useMutation({
    mutationFn: ({ uuid, status }: { uuid: string; status: TriageStatus }) =>
      feedbackApi.triage(uuid, status),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.summary });
      void qc.invalidateQueries({ queryKey: KEYS.list });
    },
  });

  const exportCases = async (): Promise<void> => {
    const cases = await feedbackApi.regressionCases();
    const jsonl = cases.map((c) => JSON.stringify(c)).join('\n');
    const url = URL.createObjectURL(new Blob([jsonl], { type: 'application/jsonl' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'feedback_regression_cases.jsonl';
    a.click();
    URL.revokeObjectURL(url);
  };

  const s = summary.data;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-heading font-bold text-text">{t('feedbackOps.title')}</h1>
        <button
          type="button"
          onClick={() => void exportCases()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-small font-semibold cursor-pointer"
        >
          <Download className="w-4 h-4" aria-hidden="true" />
          {t('feedbackOps.exportRegression')}
        </button>
      </div>

      {summary.isError && <p role="alert" className="text-small text-danger-700">{t('chat.error')}</p>}
      {s && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Stat label={t('feedbackOps.total')} value={s.total} />
            <Stat label={t('feedbackOps.pendingTriage')} value={s.pending_triage} />
            <Stat
              label={t('feedbackOps.downRate')}
              value={s.breakdown.all?.[0] ? `${Math.round(s.breakdown.all[0].down_rate * 100)}%` : '—'}
            />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Breakdown title={t('feedbackOps.byLanguage')} rows={s.breakdown.language ?? []} />
            <Breakdown title={t('feedbackOps.byIntent')} rows={s.breakdown.intent ?? []} />
            <section className="rounded-xl border border-border bg-surface p-3">
              <h2 className="text-small font-bold text-text mb-2">{t('feedbackOps.reasons')}</h2>
              {Object.keys(s.down_reasons).length === 0 ? (
                <p className="text-caption text-text-muted">—</p>
              ) : (
                <ul className="text-caption space-y-1">
                  {Object.entries(s.down_reasons)
                    .sort((a, b) => b[1] - a[1])
                    .map(([reason, n]) => (
                      <li key={reason} className="flex justify-between">
                        <span>{t(`chat.reasons.${reason}`, { defaultValue: reason })}</span>
                        <span className="font-semibold">{n}</span>
                      </li>
                    ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}

      <section className="space-y-2">
        <h2 className="text-body font-bold text-text">{t('feedbackOps.flagged')}</h2>
        {flagged.data?.length === 0 && (
          <p className="text-small text-text-muted">{t('feedbackOps.nothingToTriage')}</p>
        )}
        <ul className="space-y-2">
          {(flagged.data ?? []).map((f) => (
            <li key={f.uuid} className="rounded-xl border border-border bg-surface p-3 space-y-1.5">
              <p className="text-caption text-text-muted">
                {[f.language, f.intent, f.reason && t(`chat.reasons.${f.reason}`, { defaultValue: f.reason })]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              {f.question && <p className="text-small font-semibold text-text">{f.question}</p>}
              {f.answer && <p className="text-small text-text-secondary whitespace-pre-line">{f.answer}</p>}
              {f.comment && <p className="text-caption italic text-text-secondary">“{f.comment}”</p>}
              <div className="flex flex-wrap gap-2 pt-1">
                {(['converted_to_regression', 'triaged', 'dismissed'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    disabled={triage.isPending}
                    onClick={() => triage.mutate({ uuid: f.uuid, status: st })}
                    className="px-2.5 py-1 rounded-lg border border-border text-caption font-semibold cursor-pointer disabled:opacity-50"
                  >
                    {t(`feedbackOps.actions.${st}`)}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-xl border border-border bg-surface p-3">
    <p className="text-caption text-text-muted">{label}</p>
    <p className="text-heading font-bold text-text">{value}</p>
  </div>
);

const Breakdown: React.FC<{ title: string; rows: FeedbackBreakdownRow[] }> = ({ title, rows }) => {
  const { t } = useTranslation();
  return (
    <section className="rounded-xl border border-border bg-surface p-3">
      <h2 className="text-small font-bold text-text mb-2">{title}</h2>
      <table className="w-full text-caption">
        <thead>
          <tr className="text-text-muted text-left">
            <th className="font-medium" />
            <th className="font-medium text-right">{t('feedbackOps.count')}</th>
            <th className="font-medium text-right">{t('feedbackOps.downRate')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.value}>
              <td>{r.value}</td>
              <td className="text-right tabular-nums">{r.count}</td>
              <td className="text-right tabular-nums">{Math.round(r.down_rate * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
};

export default FeedbackDashboardPage;
