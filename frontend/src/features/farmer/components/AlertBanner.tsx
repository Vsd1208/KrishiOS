/**
 * AlertBanner Component.
 *
 * Displays top active proactive notifications on the Farmer Home page.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight } from 'lucide-react';
import { AlertCard } from '@/features/farmer/components/AlertCard';
import type { AlertNotification } from '@/types/proactive';

interface AlertBannerProps {
  alerts: AlertNotification[];
  onAcknowledge?: (alertId: number) => void;
  isAcknowledging?: boolean;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  alerts,
  onAcknowledge,
  isAcknowledging,
}) => {
  const navigate = useNavigate();
  const unacknowledged = alerts.filter((a) => a.status !== 'ACKNOWLEDGED');

  if (unacknowledged.length === 0) {
    return null;
  }

  return (
    <section aria-label="Urgent Agricultural Advisories" className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-danger-100 text-danger-700 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4" aria-hidden="true" />
          </div>
          <h2 className="text-small font-bold uppercase tracking-wider text-danger-900">
            Active Crop & Weather Alerts ({unacknowledged.length})
          </h2>
        </div>

        <button
          type="button"
          onClick={() => navigate('/farmer/alerts')}
          className="text-caption font-semibold text-primary-600 hover:text-primary-700 inline-flex items-center gap-1 cursor-pointer"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
      </div>

      <div className="space-y-2">
        {unacknowledged.slice(0, 2).map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onAcknowledge={onAcknowledge}
            isAcknowledging={isAcknowledging}
          />
        ))}
      </div>
    </section>
  );
};

export default AlertBanner;
