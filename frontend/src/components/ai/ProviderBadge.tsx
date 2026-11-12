/**
 * ProviderBadge: shows a provider's name, version and whether it is live, sandbox or mock.
 * A mock is never styled like a live provider.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import type { ProviderKind } from '@/services/api/providers';

interface ProviderBadgeProps {
  name: string | null;
  version?: string | null;
  kind: ProviderKind | null;
  className?: string;
}

const KIND_STYLES: Record<ProviderKind, string> = {
  live: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  sandbox: 'bg-amber-50 text-amber-800 border-amber-200',
  mock: 'bg-red-50 text-red-800 border-red-300',
};

export const ProviderBadge: React.FC<ProviderBadgeProps> = ({
  name,
  version,
  kind,
  className = '',
}) => {
  const { t } = useTranslation();
  if (!name || !kind) {
    return (
      <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-caption border-border text-text-muted ${className}`}>
        {t('providers.notConfigured')}
      </span>
    );
  }
  return (
    <span
      data-kind={kind}
      title={`${name}${version ? ` v${version}` : ''}`}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-caption font-medium ${KIND_STYLES[kind]} ${className}`}
    >
      <span className="font-mono">{name}</span>
      {version ? <span className="opacity-70">v{version}</span> : null}
      <span className="uppercase tracking-wide">· {t(`providers.${kind}`)}</span>
    </span>
  );
};

export default ProviderBadge;
