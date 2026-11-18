/** What the local image model saw in the farmer's photo: the crop (and whether the farmer
 * confirmed it) and up to three possible conditions with confidence. Always labelled as
 * possibilities from a model, not a diagnosis. */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Camera } from 'lucide-react';

import type { VisionCard as Vision } from '@/services/api/conversation';

export const VisionCard: React.FC<{ vision: Vision; cropName?: string }> = ({ vision, cropName }) => {
  const { t } = useTranslation();
  const conds = vision.candidate_conditions.slice(0, 3);
  return (
    <section aria-label={t('photo.title')} className="rounded-xl border border-border bg-surface p-3 space-y-1.5" data-testid="vision-card">
      <h3 className="flex items-center gap-1.5 text-caption font-bold uppercase text-text-secondary">
        <Camera className="w-3.5 h-3.5" aria-hidden="true" />
        {t('photo.title')} · {cropName ?? vision.crop ?? '—'}
        {vision.crop_confirmed_by_farmer && <span className="font-normal normal-case"> ({t('photo.confirmed')})</span>}
      </h3>
      {conds.length === 0 ? (
        <p className="text-small text-text-muted">{t('photo.noFindings')}</p>
      ) : (
        <ul className="space-y-1">
          {conds.map((c) => (
            <li key={c.name} className="flex items-center gap-2 text-small">
              <span className="flex-1 capitalize text-text">{c.name}</span>
              <span className="w-24 h-1.5 rounded bg-surface-raised overflow-hidden" aria-hidden="true">
                <span className="block h-full bg-primary-500" style={{ width: `${Math.round(c.confidence * 100)}%` }} />
              </span>
              <span className="w-10 text-right tabular-nums text-text-secondary">{Math.round(c.confidence * 100)}%</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-caption text-text-muted">{t('photo.notDiagnosis')}</p>
      <p className="text-caption text-text-muted">
        {t('photo.model', { model: vision.model_name, version: vision.model_version })}
      </p>
    </section>
  );
};

export default VisionCard;
