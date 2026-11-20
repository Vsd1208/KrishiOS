/**
 * FieldsPage: the signed-in farmer's registered fields, with the latest soil test for each when
 * one exists. Missing values show a dash; there are no sample plots or sample soil results.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { MapPin, FlaskConical, Sprout } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/feedback/EmptyState';
import { ErrorState } from '@/components/feedback/ErrorState';
import {
  FARMER_QUERY_KEYS,
  useFarmerCrops,
  useFarmerProfile,
  useFarmerFields,
} from '@/features/farmer/hooks/useFarmerData';
import { farmerApi } from '@/services/api/farmer';
import type { SoilSample } from '@/types/domain';

const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));

function latestByField(samples: SoilSample[]): Map<number, SoilSample> {
  const out = new Map<number, SoilSample>();
  for (const s of samples) {
    const prev = out.get(s.field_id);
    if (!prev || s.collected_at > prev.collected_at) out.set(s.field_id, s);
  }
  return out;
}

export const FieldsPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { data: farmer, isLoading: isFarmerLoading, isError: farmerError, refetch } = useFarmerProfile();
  const { data: fields = [], isLoading: isFieldsLoading, isError: fieldsError } = useFarmerFields(farmer?.id ?? undefined);
  const { crops, fieldCrops } = useFarmerCrops();
  const soil = useQuery({
    queryKey: FARMER_QUERY_KEYS.soilSamples,
    queryFn: () => farmerApi.listSoilSamples(),
    enabled: fields.length > 0,
    staleTime: 10 * 60 * 1000,
  });
  const latest = latestByField(soil.data ?? []);
  const fmtDate = (iso: string) =>
    new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' }).format(new Date(iso));

  const isLoading = isFarmerLoading || (farmer && isFieldsLoading);
  const totalAcres = farmer?.landholding_acres;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">{t('fieldsPage.title')}</h1>
          <p className="text-body text-text-secondary">{t('fieldsPage.subtitle')}</p>
        </div>
        {totalAcres !== undefined && totalAcres !== null && (
          <div className="text-caption text-text-muted">
            {t('fieldsPage.totalLand')}{' '}
            <strong className="text-text font-bold">{t('fieldsPage.acres', { n: totalAcres })}</strong>
          </div>
        )}
      </div>

      {farmerError || fieldsError ? (
        <ErrorState title={t('errors.serverError')} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map((i) => (
            <Card key={i} variant="default" padding="md">
              <Skeleton width="60%" height={24} />
            </Card>
          ))}
        </div>
      ) : !farmer ? (
        <EmptyState title={t('profile.noProfile')} />
      ) : fields.length === 0 ? (
        <EmptyState
          icon={<MapPin className="w-6 h-6" aria-hidden="true" />}
          title={t('fieldsPage.none')}
          message={t('fieldsPage.noneHelp')}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fields.map((field) => {
            const sample = latest.get(field.id);
            const onField = fieldCrops.filter((fc) => fc.field_id === field.id);
            return (
              <Card key={field.id} variant="raised" padding="md" className="border-t-4 border-t-primary-600 space-y-3">
                <CardHeader className="pb-1">
                  <CardTitle as="h2" className="text-subheading font-bold text-text break-words">
                    {field.field_name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 pt-0 text-caption">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div className="p-2 rounded-lg bg-surface-raised border border-border">
                      <span className="text-text-muted block">{t('fieldsPage.area')}</span>
                      <strong className="text-text font-bold">
                        {field.area_acres ? t('fieldsPage.acres', { n: field.area_acres }) : '—'}
                      </strong>
                    </div>
                    <div className="p-2 rounded-lg bg-surface-raised border border-border">
                      <span className="text-text-muted block">{t('fieldsPage.soilType')}</span>
                      <strong className="text-text font-bold">{dash(field.soil_type)}</strong>
                    </div>
                    <div className="p-2 rounded-lg bg-surface-raised border border-border">
                      <span className="text-text-muted block">{t('fieldsPage.irrigation')}</span>
                      <strong className="text-text font-bold">{dash(field.irrigation_type)}</strong>
                    </div>
                  </div>

                  {onField.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Sprout className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                      {onField.map((fc) => {
                        const crop = crops.find((c) => c.id === fc.crop_id);
                        return (
                          <span key={fc.id} className="px-2 py-0.5 rounded-full bg-primary-50 text-primary-800 border border-primary-200">
                            {[crop?.crop_name || crop?.name, fc.season, fc.year].filter(Boolean).join(' · ')}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  <div className="p-3 rounded-lg bg-surface-raised border border-border space-y-1">
                    <span className="flex items-center gap-1.5 font-semibold text-text">
                      <FlaskConical className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                      {t('fieldsPage.soilTest')}
                    </span>
                    {sample ? (
                      <>
                        <p className="text-text-muted">{t('fieldsPage.tested', { date: fmtDate(sample.collected_at) })}</p>
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-x-3 gap-y-0.5 text-text">
                          <span>pH {dash(sample.ph)}</span>
                          <span>N {dash(sample.nitrogen_kg_ha)} kg/ha</span>
                          <span>P {dash(sample.phosphorus_kg_ha)} kg/ha</span>
                          <span>K {dash(sample.potassium_kg_ha)} kg/ha</span>
                          <span>OC {dash(sample.organic_carbon_pct)}%</span>
                        </div>
                      </>
                    ) : (
                      <p className="text-text-muted">{soil.isError ? t('fieldsPage.soilFailed') : t('fieldsPage.noSoil')}</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default FieldsPage;
