/**
 * F8 outbreak surveillance (Phase 9): a district x week heat grid of distinct farmers whose
 * photos the local model read as each condition, with this week's possible outbreaks first.
 * Possible outbreaks become review drafts in Bulletins; nothing reaches farmers until an
 * officer approves it. Counts are unverified model findings, not diagnoses.
 */

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { surveillanceApi, type HeatCell } from '@/services/api/surveillance';

const WEEKS = 8;

function shade(n: number, max: number): string {
  if (n === 0) return 'transparent';
  const a = 0.15 + 0.85 * Math.min(1, n / Math.max(max, 1));
  return `rgba(220, 38, 38, ${a.toFixed(2)})`;
}

export const OutbreakMapPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const grid = useQuery({ queryKey: ['surveillance', 'heatmap', WEEKS], queryFn: () => surveillanceApi.heatmap(WEEKS) });
  const outbreaks = useQuery({ queryKey: ['surveillance', 'outbreaks'], queryFn: surveillanceApi.outbreaks });

  const { weeks, rows, max } = useMemo(() => {
    const cells = grid.data?.cells ?? [];
    const ws = [...new Set(cells.map((c) => c.week_start))].sort();
    const byRow = new Map<string, { label: HeatCell; counts: Record<string, number> }>();
    for (const c of cells) {
      const key = `${c.lgd_district_code}|${c.crop}|${c.condition}`;
      const row = byRow.get(key) ?? { label: c, counts: {} };
      row.counts[c.week_start] = c.reporters;
      byRow.set(key, row);
    }
    const last = ws[ws.length - 1] ?? '';
    const sorted = [...byRow.values()].sort((a, b) => (b.counts[last] ?? 0) - (a.counts[last] ?? 0));
    return { weeks: ws, rows: sorted, max: Math.max(0, ...cells.map((c) => c.reporters)) };
  }, [grid.data]);

  const fmt = (d: string) => new Intl.DateTimeFormat(i18n.language, { day: 'numeric', month: 'short' }).format(new Date(d));

  return (
    <div className="space-y-5">
      <h1 className="text-heading font-bold text-text">{t('outbreak.title')}</h1>
      <p className="text-small text-text-secondary">{t('outbreak.intro')}</p>

      <section className="rounded-2xl border border-border bg-surface p-4 space-y-2">
        <h2 className="text-caption font-bold uppercase text-text-secondary">{t('outbreak.thisWeek')}</h2>
        {(outbreaks.data?.items ?? []).length === 0 ? (
          <p className="text-small text-text-muted">{t('outbreak.none')}</p>
        ) : (
          <ul className="space-y-1">
            {outbreaks.data!.items.map((o) => (
              <li key={`${o.lgd_district_code}-${o.crop}-${o.condition}`} className="text-small text-text">
                <strong className="capitalize">{o.condition}</strong> · {o.crop_name} · {o.district_name ?? o.lgd_district_code}:{' '}
                {t('outbreak.reporters', { n: o.reporters, base: o.baseline.toFixed(1) })}
              </li>
            ))}
          </ul>
        )}
        <Link to="/officer/bulletins" className="inline-block text-small font-semibold text-primary-700 hover:underline">
          {t('outbreak.reviewDrafts')}
        </Link>
      </section>

      {rows.length === 0 ? (
        <p className="text-small text-text-muted">{t('outbreak.noReports')}</p>
      ) : (
        <section className="overflow-x-auto rounded-2xl border border-border bg-surface" aria-label={t('outbreak.gridLabel')}>
          <table className="w-full text-caption">
            <thead className="text-left text-text-muted">
              <tr>
                <th className="p-2 font-medium">{t('outbreak.where')}</th>
                {weeks.map((w) => (
                  <th key={w} className="p-2 font-medium text-center">{fmt(w)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ label, counts }) => (
                <tr key={`${label.lgd_district_code}-${label.crop}-${label.condition}`} className="border-t border-border">
                  <td className="p-2">
                    <span className="font-semibold text-text capitalize">{label.condition}</span> · {label.crop_name}
                    <span className="block text-text-muted">{label.district_name ?? label.lgd_district_code}</span>
                  </td>
                  {weeks.map((w) => (
                    <td key={w} className="p-2 text-center tabular-nums" style={{ background: shade(counts[w] ?? 0, max) }}>
                      {counts[w] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <p className="text-caption text-text-muted">{grid.data?.note ?? t('outbreak.note')}</p>
    </div>
  );
};

export default OutbreakMapPage;
