/** Dashboard card: active HIGH/CRITICAL official warnings for the farmer's places. */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Landmark } from 'lucide-react';

import { govconnectApi } from '@/services/api/govconnect';
import { formatDate, SEVERITY_STYLE } from './format';

export const ActiveWarningsCard: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { data = [] } = useQuery({
    queryKey: ['govconnect', 'inbox', false],
    queryFn: () => govconnectApi.inbox(true),
  });
  const warnings = data.filter((i) => i.severity === 'HIGH' || i.severity === 'CRITICAL');
  if (warnings.length === 0) return null;
  return (
    <section
      aria-label={t('govt.activeWarnings')}
      className="rounded-2xl border-2 border-info-200 bg-surface p-4 space-y-2"
    >
      <h2 className="text-body font-bold text-text flex items-center gap-2">
        <Landmark className="w-4 h-4 text-info-700" aria-hidden="true" />
        {t('govt.activeWarnings')}
      </h2>
      <ul className="space-y-1.5">
        {warnings.slice(0, 3).map((w) => (
          <li key={w.bulletin_uuid} className="flex items-start gap-2 text-small">
            <span className={`shrink-0 px-2 py-0.5 rounded-full text-caption font-bold ${SEVERITY_STYLE[w.severity]}`}>
              {t(`govt.severity.${w.severity}`)}
            </span>
            <span>
              <span className="font-semibold text-text">{w.title}</span>
              <span className="block text-caption text-text-muted">
                {w.authority} · {t('govt.validUntil')} {formatDate(w.valid_to, i18n.language)}
              </span>
            </span>
          </li>
        ))}
      </ul>
      <Link to="/farmer/updates" className="text-caption text-info-700 underline">
        {t('govt.openUpdates')}
      </Link>
    </section>
  );
};
