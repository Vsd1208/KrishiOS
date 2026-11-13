import React from 'react';
import { useTranslation } from 'react-i18next';

import type { Ticket } from '@/services/api/grievance';

export const StatusChip: React.FC<{ ticket: Ticket }> = ({ ticket }) => {
  const { t } = useTranslation();
  return (
    <span className="flex items-center gap-1">
      {ticket.breached && ticket.hours_left !== null && (
        <span className="px-2 py-0.5 rounded-full bg-danger-50 text-danger-700 text-caption font-semibold">
          {t('help.overdue')}
        </span>
      )}
      <span className="px-2 py-0.5 rounded-full bg-surface-raised text-caption font-semibold text-text-secondary">
        {t(`help.status.${ticket.status}`)}
      </span>
    </span>
  );
};
