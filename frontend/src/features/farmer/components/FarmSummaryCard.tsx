/**
 * FarmSummaryCard Component.
 *
 * Displays farmer profile summary, registered landholding acreage,
 * village/district location, and active field plot count.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { MapPin, Sprout, Layers } from 'lucide-react';
import type { Farmer, Field, FieldCrop } from '@/types/domain';

interface FarmSummaryCardProps {
  farmer: Farmer | null | undefined;
  fields: Field[];
  fieldCrops: FieldCrop[];
  isLoading?: boolean;
}

export const FarmSummaryCard: React.FC<FarmSummaryCardProps> = ({
  farmer,
  fields,
  fieldCrops,
  isLoading,
}) => {
  const { t } = useTranslation();
  if (isLoading) {
    return (
      <Card variant="raised" padding="md">
        <div className="space-y-3">
          <Skeleton width="40%" height={24} />
          <Skeleton width="70%" height={18} />
          <div className="grid grid-cols-3 gap-3 pt-2">
            <Skeleton height={50} />
            <Skeleton height={50} />
            <Skeleton height={50} />
          </div>
        </div>
      </Card>
    );
  }

  const activeCropsCount = fieldCrops.filter((fc) => ['growing', 'sown'].includes(fc.status.toLowerCase())).length;
  const fieldAcres = fields.reduce((acc, f) => acc + (Number(f.area_acres) || 0), 0);
  const totalAcres = farmer?.landholding_acres ? Number(farmer.landholding_acres) : fieldAcres || null;

  return (
    <Card variant="raised" padding="md" className="border-l-4 border-l-primary-600">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-1.5 text-text-secondary text-caption">
              <MapPin className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <span className="truncate">{farmer?.village || '—'}</span>
            </div>
            <CardTitle as="h2" className="text-subheading font-bold text-text mt-0.5">
              {farmer?.full_name || t('farmSummary.title')}
            </CardTitle>
          </div>

        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="grid grid-cols-3 gap-2 sm:gap-4 p-3 bg-surface-raised rounded-lg border border-border">
          <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
            <span className="text-caption text-text-muted">{t('farmSummary.land')}</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-heading font-bold text-text">{totalAcres === null ? '—' : totalAcres.toFixed(1)}</span>
              <span className="text-caption text-text-secondary">{t('farmSummary.acres')}</span>
            </div>
          </div>

          <div className="flex flex-col items-center sm:items-start text-center sm:text-left border-x border-border px-2">
            <span className="text-caption text-text-muted">{t('farmSummary.fields')}</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Layers className="w-4 h-4 text-primary-600 hidden sm:inline" aria-hidden="true" />
              <span className="text-heading font-bold text-text">{fields.length}</span>
            </div>
          </div>

          <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
            <span className="text-caption text-text-muted">{t('farmSummary.standing')}</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Sprout className="w-4 h-4 text-success-600 hidden sm:inline" aria-hidden="true" />
              <span className="text-heading font-bold text-success-700">
                {activeCropsCount}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default FarmSummaryCard;
