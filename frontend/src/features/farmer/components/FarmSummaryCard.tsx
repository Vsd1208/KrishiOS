/**
 * FarmSummaryCard Component.
 *
 * Displays farmer profile summary, registered landholding acreage,
 * village/district location, and active field plot count.
 */

import React from 'react';
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

  const activeCropsCount = fieldCrops.filter((fc) => fc.status !== 'HARVESTED').length;
  const totalAcres = farmer?.landholding_acres || fields.reduce((acc, f) => acc + (f.area_acres || 0), 0);

  return (
    <Card variant="raised" padding="md" className="border-l-4 border-l-primary-600">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-1.5 text-text-secondary text-caption">
              <MapPin className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <span className="truncate">
                {farmer?.village ? `${farmer.village}, District #${farmer.district_id}` : 'Local Farm'}
              </span>
            </div>
            <CardTitle as="h2" className="text-subheading font-bold text-text mt-0.5">
              {farmer?.full_name || 'My Farm Overview'}
            </CardTitle>
          </div>

          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-caption font-medium bg-primary-50 text-primary-700 border border-primary-200 self-start sm:self-auto">
            <span className="w-2 h-2 rounded-full bg-primary-600 animate-pulse" aria-hidden="true" />
            Verified Farmer
          </span>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="grid grid-cols-3 gap-2 sm:gap-4 p-3 bg-surface-raised rounded-lg border border-border">
          <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
            <span className="text-caption text-text-muted">Landholding</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-heading font-bold text-text">{Number(totalAcres).toFixed(1)}</span>
              <span className="text-caption text-text-secondary">Acres</span>
            </div>
          </div>

          <div className="flex flex-col items-center sm:items-start text-center sm:text-left border-x border-border px-2">
            <span className="text-caption text-text-muted">Plots</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Layers className="w-4 h-4 text-primary-600 hidden sm:inline" aria-hidden="true" />
              <span className="text-heading font-bold text-text">{fields.length}</span>
              <span className="text-caption text-text-secondary">Fields</span>
            </div>
          </div>

          <div className="flex flex-col items-center sm:items-start text-center sm:text-left">
            <span className="text-caption text-text-muted">Standing Crops</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Sprout className="w-4 h-4 text-success-600 hidden sm:inline" aria-hidden="true" />
              <span className="text-heading font-bold text-success-700">
                {activeCropsCount || fields.length || 1}
              </span>
              <span className="text-caption text-text-secondary">Active</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default FarmSummaryCard;
