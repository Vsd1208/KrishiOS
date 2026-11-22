/**
 * AdvisoryActionToolbar: print the answer, or take the question to an officer.
 *
 * "Ask an officer" opens Help, where the farmer raises a ticket that reaches the officer's
 * grievance queue. Nothing here claims a question was sent; the ticket screen confirms that.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Printer, Send } from 'lucide-react';

interface AdvisoryActionToolbarProps {
  advisoryText: string;
  crop?: string;
  onEscalate?: () => void;
}

export const AdvisoryActionToolbar: React.FC<AdvisoryActionToolbarProps> = ({ onEscalate }) => {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border text-caption">
      <button
        type="button"
        onClick={() => window.print()}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-raised text-text-secondary border border-border cursor-pointer transition-colors"
      >
        <Printer className="w-3.5 h-3.5" aria-hidden="true" />
        <span>{t('ai.print')}</span>
      </button>

      {onEscalate && (
        <button
          type="button"
          onClick={onEscalate}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border ml-auto cursor-pointer bg-primary-50 hover:bg-primary-100 text-primary-800 border-primary-200"
        >
          <Send className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
          <span className="font-bold">{t('ai.askOfficer')}</span>
        </button>
      )}
    </div>
  );
};

export default AdvisoryActionToolbar;
