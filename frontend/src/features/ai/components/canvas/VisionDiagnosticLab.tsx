/**
 * VisionDiagnosticLab: the photo attached in this chat. Chat answers do not yet carry the photo
 * check's findings, so this tab shows the photo and points to "Add a crop photo", which runs the
 * offline crop and disease models and asks the farmer to confirm the crop. No findings are invented.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Eye, ShieldAlert } from 'lucide-react';
import type { ImageAttachment } from '@/features/ai/types/conversation';

interface VisionDiagnosticLabProps {
  image?: ImageAttachment;
  crop?: string;
}

export const VisionDiagnosticLab: React.FC<VisionDiagnosticLabProps> = ({ image }) => {
  const { t } = useTranslation();
  const finding = image?.diagnosisCondition;
  const conf = image?.diagnosisConfidence;

  return (
    <div className="space-y-4 animate-fadeIn">
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700">
          <Eye className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-small font-bold text-text">{t('canvas.vision.title')}</h4>
          <p className="text-caption text-text-muted">{t('canvas.vision.subtitle')}</p>
        </div>
      </div>

      {image ? (
        <div className="rounded-xl overflow-hidden border border-border bg-surface-raised">
          <img src={image.previewUrl} alt={t('canvas.vision.alt')} className="w-full max-h-56 object-cover" />
          <p className="p-2 border-t border-border text-caption font-semibold text-text truncate">{image.file.name}</p>
        </div>
      ) : (
        <div
          className="p-6 rounded-xl border border-dashed border-border bg-surface-raised text-center space-y-2"
          data-testid="no-photo"
        >
          <Eye className="w-8 h-8 text-text-muted mx-auto opacity-60" aria-hidden="true" />
          <p className="text-small text-text-secondary font-medium">{t('canvas.vision.none')}</p>
        </div>
      )}

      {finding ? (
        <div className="p-3 rounded-xl bg-surface border border-border">
          <span className="text-caption text-text-muted block">{t('canvas.vision.possible')}</span>
          <span className="text-small font-bold text-text">{finding}</span>
          {typeof conf === 'number' && (
            <span className="text-caption text-text-secondary">
              {' · '}
              {t('canvas.vision.confidence', { pct: Math.round(conf * 100) })}
            </span>
          )}
        </div>
      ) : (
        image && (
          <p className="text-caption text-text-secondary" data-testid="vision-howto">
            {t('canvas.vision.howto', { chat: t('chat.simpleChat') })}
          </p>
        )
      )}

      <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-caption text-amber-900 flex items-start gap-2">
        <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
        <span>{t('canvas.vision.caution')}</span>
      </div>
    </div>
  );
};

export default VisionDiagnosticLab;
