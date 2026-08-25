/**
 * FieldsPage Component.
 *
 * Overview of registered farm plots, soil health metrics (pH, NPK),
 * irrigation types, and standing crops.
 */

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  useFarmerProfile,
  useFarmerFields,
} from '@/features/farmer/hooks/useFarmerData';
import { MapPin, FlaskConical } from 'lucide-react';

export const FieldsPage: React.FC = () => {
  const { data: farmer, isLoading: isFarmerLoading } = useFarmerProfile();
  const { data: fields = [], isLoading: isFieldsLoading } = useFarmerFields(farmer?.id);

  const isLoading = isFarmerLoading || isFieldsLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">My Farm Plots</h1>
          <p className="text-body text-text-secondary">
            Registered landholdings, soil conditions, and crop rotations
          </p>
        </div>
        <div className="text-caption text-text-muted">
          Total Acreage: <strong className="text-text font-bold">{farmer?.landholding_acres || 5.5} Acres</strong>
        </div>
      </div>

      {/* Plots Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card variant="default" padding="md">
            <Skeleton width="60%" height={24} />
            <Skeleton height={100} className="mt-3" />
          </Card>
          <Card variant="default" padding="md">
            <Skeleton width="60%" height={24} />
            <Skeleton height={100} className="mt-3" />
          </Card>
        </div>
      ) : fields.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Default Plot 1 */}
          <Card variant="raised" padding="md" className="border-t-4 border-t-primary-600 space-y-4">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1 text-caption text-text-muted">
                    <MapPin className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                    <span>North Field • Plot #1</span>
                  </div>
                  <CardTitle as="h2" className="text-subheading font-bold text-text mt-0.5">
                    Paddy Plot (BPT 5204)
                  </CardTitle>
                </div>
                <span className="px-2.5 py-1 rounded-full text-caption font-semibold bg-success-50 text-success-700 border border-success-200">
                  Optimal Health
                </span>
              </div>
            </CardHeader>

            <CardContent className="space-y-3 pt-0">
              <div className="grid grid-cols-2 gap-2 text-caption">
                <div className="p-2.5 rounded-lg bg-surface-raised border border-border">
                  <span className="text-text-muted block">Area</span>
                  <strong className="text-text font-bold">3.5 Acres</strong>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-raised border border-border">
                  <span className="text-text-muted block">Irrigation</span>
                  <strong className="text-text font-bold">Borewell &amp; Drip</strong>
                </div>
              </div>

              {/* Soil Health Snapshot */}
              <div className="p-3 rounded-lg bg-surface-raised border border-border space-y-1.5">
                <div className="flex items-center justify-between text-caption font-semibold text-text">
                  <div className="flex items-center gap-1.5 text-primary-700">
                    <FlaskConical className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Soil Health Profile</span>
                  </div>
                  <span className="text-success-700">pH 6.8 (Neutral)</span>
                </div>
                <div className="flex items-center justify-between text-caption text-text-secondary pt-1 border-t border-border">
                  <span>Nitrogen (N): Medium</span>
                  <span>Phosphorus (P): High</span>
                  <span>Potassium (K): Adequate</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Default Plot 2 */}
          <Card variant="raised" padding="md" className="border-t-4 border-t-accent-600 space-y-4">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1 text-caption text-text-muted">
                    <MapPin className="w-3.5 h-3.5 text-accent-600" aria-hidden="true" />
                    <span>South Field • Plot #2</span>
                  </div>
                  <CardTitle as="h2" className="text-subheading font-bold text-text mt-0.5">
                    Cotton Plot (Bt Hybrid)
                  </CardTitle>
                </div>
                <span className="px-2.5 py-1 rounded-full text-caption font-semibold bg-warning-50 text-warning-700 border border-warning-200">
                  Advisory Active
                </span>
              </div>
            </CardHeader>

            <CardContent className="space-y-3 pt-0">
              <div className="grid grid-cols-2 gap-2 text-caption">
                <div className="p-2.5 rounded-lg bg-surface-raised border border-border">
                  <span className="text-text-muted block">Area</span>
                  <strong className="text-text font-bold">2.0 Acres</strong>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-raised border border-border">
                  <span className="text-text-muted block">Irrigation</span>
                  <strong className="text-text font-bold">Canal &amp; Rainfed</strong>
                </div>
              </div>

              {/* Soil Health Snapshot */}
              <div className="p-3 rounded-lg bg-surface-raised border border-border space-y-1.5">
                <div className="flex items-center justify-between text-caption font-semibold text-text">
                  <div className="flex items-center gap-1.5 text-accent-700">
                    <FlaskConical className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Soil Health Profile</span>
                  </div>
                  <span className="text-warning-700">pH 7.4 (Slightly Alkaline)</span>
                </div>
                <div className="flex items-center justify-between text-caption text-text-secondary pt-1 border-t border-border">
                  <span>Nitrogen (N): Low</span>
                  <span>Phosphorus (P): Medium</span>
                  <span>Potassium (K): High</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fields.map((field) => (
            <Card
              key={field.id}
              variant="raised"
              padding="md"
              className="border-t-4 border-t-primary-600 space-y-3"
            >
              <CardHeader className="pb-1">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-1 text-caption text-text-muted">
                      <MapPin className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                      <span>Plot #{field.id}</span>
                    </div>
                    <CardTitle as="h2" className="text-subheading font-bold text-text mt-0.5">
                      {field.field_name}
                    </CardTitle>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-caption font-semibold bg-primary-50 text-primary-700 border border-primary-200">
                    Registered
                  </span>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 pt-0">
                <div className="grid grid-cols-2 gap-2 text-caption">
                  <div className="p-2 rounded-lg bg-surface-raised border border-border">
                    <span className="text-text-muted block">Area</span>
                    <strong className="text-text font-bold">{field.area_acres} Acres</strong>
                  </div>
                  <div className="p-2 rounded-lg bg-surface-raised border border-border">
                    <span className="text-text-muted block">Soil Type</span>
                    <strong className="text-text font-bold">{field.soil_type || 'Black Soil'}</strong>
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-raised border border-border text-caption text-text-secondary">
                  <span>Irrigation: </span>
                  <strong className="text-text">{field.irrigation_type || 'Borewell'}</strong>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default FieldsPage;
