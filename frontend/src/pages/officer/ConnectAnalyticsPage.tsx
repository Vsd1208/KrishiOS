/** Govt Connect analytics (Phase 4): delivery, read, acknowledgement, flags and farmer
 * questions per published bulletin, plus the farmer flag queue. Real runs only. */

import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { formatDate } from '@/features/govconnect/format';
import { govconnectApi } from '@/services/api/govconnect';

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`);

export const ConnectAnalyticsPage: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const stats = useQuery({ queryKey: ['govconnect', 'analytics'], queryFn: govconnectApi.analytics });
  const flags = useQuery({ queryKey: ['govconnect', 'flags'], queryFn: () => govconnectApi.flags() });
  const triage = useMutation({
    mutationFn: (p: { id: number; status: 'reviewed' | 'dismissed' }) => govconnectApi.triageFlag(p.id, p.status),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['govconnect', 'flags'] });
      void qc.invalidateQueries({ queryKey: ['govconnect', 'analytics'] });
    },
  });

  return (
    <div className="space-y-5">
      <h1 className="text-heading font-bold text-text">{t('gc.analyticsTitle')}</h1>
      <section className="overflow-x-auto rounded-2xl border border-border bg-surface">
        <table className="w-full text-caption">
          <thead className="text-left text-text-muted">
            <tr>
              <th className="p-2 font-medium">{t('gc.bulletin')}</th>
              <th className="p-2 font-medium text-right">{t('gc.recipients')}</th>
              <th className="p-2 font-medium text-right">{t('gc.notified')}</th>
              <th className="p-2 font-medium text-right">{t('gc.readRate')}</th>
              <th className="p-2 font-medium text-right">{t('gc.ackRate')}</th>
              <th className="p-2 font-medium text-right">{t('gc.flagRate')}</th>
              <th className="p-2 font-medium text-right">{t('gc.questions')}</th>
            </tr>
          </thead>
          <tbody>
            {(stats.data ?? []).map((s) => (
              <tr key={s.uuid} className="border-t border-border">
                <td className="p-2">
                  <Link to={`/officer/bulletins?open=${s.uuid}`} className="font-semibold text-text hover:underline">
                    {s.title}
                  </Link>
                  <span className="block text-text-muted">
                    {t(`gc.status.${s.status}`)} · {formatDate(s.published_at, 'en')}
                  </span>
                </td>
                <td className="p-2 text-right tabular-nums">{s.recipients}</td>
                <td className="p-2 text-right tabular-nums">
                  {s.notified}
                  {s.suppressed + s.deduplicated > 0 && (
                    <span className="block text-text-muted">
                      {t('gc.heldBack', { n: s.suppressed + s.deduplicated })}
                    </span>
                  )}
                </td>
                <td className="p-2 text-right tabular-nums">{pct(s.read_rate)}</td>
                <td className="p-2 text-right tabular-nums">{pct(s.ack_rate)}</td>
                <td className="p-2 text-right tabular-nums">{pct(s.flag_rate)}</td>
                <td className="p-2 text-right tabular-nums">{s.questions}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {stats.data?.length === 0 && <p className="p-3 text-small text-text-muted">{t('gc.noPublished')}</p>}
      </section>

      <section className="space-y-2">
        <h2 className="text-body font-bold text-text">{t('gc.flagQueue')}</h2>
        {flags.data?.length === 0 && <p className="text-small text-text-muted">{t('feedbackOps.nothingToTriage')}</p>}
        <ul className="space-y-2">
          {(flags.data ?? []).map((f) => (
            <li key={f.delivery_id} className="rounded-xl border border-border bg-surface p-3 space-y-1">
              <p className="text-small font-semibold text-text">{f.title}</p>
              <p className="text-caption text-text-secondary">
                {t(`govt.flagReasons.${f.reason}`, { defaultValue: f.reason ?? '' })} · {f.language} ·{' '}
                {t(`gc.match.${f.match_level}`)}
              </p>
              {f.comment && <p className="text-caption italic">“{f.comment}”</p>}
              <div className="flex gap-2">
                {(['reviewed', 'dismissed'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => triage.mutate({ id: f.delivery_id, status: st })}
                    className="px-2.5 py-1 rounded-lg border border-border text-caption font-semibold cursor-pointer"
                  >
                    {t(`gc.flagActions.${st}`)}
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

export default ConnectAnalyticsPage;
