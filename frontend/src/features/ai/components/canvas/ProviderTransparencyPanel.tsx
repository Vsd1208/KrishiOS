/**
 * ProviderTransparencyPanel: lists the active provider for every AI / data capability so
 * nothing produced by a mock or sandbox is mistaken for a live system.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ShieldAlert } from 'lucide-react';
import { getProviders } from '@/services/api/providers';
import { ProviderBadge } from '@/components/ai/ProviderBadge';

export const ProviderTransparencyPanel: React.FC = () => {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['providers'],
    queryFn: getProviders,
    staleTime: 60_000,
  });

  return (
    <section aria-label={t('providers.title')} className="space-y-3">
      <header>
        <h3 className="text-small font-bold text-text">{t('providers.title')}</h3>
        <p className="text-caption text-text-muted">{t('providers.subtitle')}</p>
      </header>

      {isLoading && <p className="text-caption text-text-muted">{t('common.loading')}</p>}
      {isError && <p className="text-caption text-red-700">{t('providers.loadError')}</p>}

      {data && (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {data.providers.map((p) => (
            <li key={p.capability} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <span className="text-caption font-semibold uppercase tracking-wide text-text-muted">
                {p.capability}
              </span>
              <span className="flex items-center gap-2">
                {p.sends_data_off_device ? (
                  <span className="text-caption text-amber-800">{t('providers.offDevice')}</span>
                ) : null}
                <ProviderBadge name={p.name} version={p.version} kind={p.kind} />
              </span>
            </li>
          ))}
        </ul>
      )}

      {data && data.policy_violations.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3">
          <p className="flex items-center gap-1 text-caption font-semibold text-amber-900">
            <ShieldAlert className="h-3.5 w-3.5" /> {t('providers.policyViolations')}
          </p>
          <ul className="mt-1 list-disc pl-5 text-caption text-amber-900">
            {data.policy_violations.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};

export default ProviderTransparencyPanel;
