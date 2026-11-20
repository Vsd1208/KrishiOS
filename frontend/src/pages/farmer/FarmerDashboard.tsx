/**
 * FarmerDashboard Page.
 *
 * Agricultural intelligence overview and primary entry point for farmers.
 * Combines farm summary, hero multimodal ask launcher, live weather & spray window,
 * and proactive crop risk alerts.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  useFarmerProfile,
  useFarmerFields,
  useFarmerCrops,
  usePrimaryFieldCrop,
  useCurrentWeather,
  useWeatherForecast,
  useFarmerAlerts,
} from '@/features/farmer/hooks/useFarmerData';
import { FarmSummaryCard } from '@/features/farmer/components/FarmSummaryCard';
import { WeatherWidget } from '@/features/farmer/components/WeatherWidget';
import { HeroActionGrid } from '@/features/farmer/components/HeroActionGrid';
import { AlertBanner } from '@/features/farmer/components/AlertBanner';
import { ActiveWarningsCard } from '@/features/govconnect/ActiveWarningsCard';
import { WeatherFeedCard } from '@/features/govconnect/WeatherFeedCard';
import { MandiTrendCard } from '@/features/govconnect/MandiTrendCard';
import { feedApi } from '@/services/api/govconnect';
import { useQuery } from '@tanstack/react-query';
import { VoiceRecorderModal } from '@/features/farmer/components/VoiceRecorderModal';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Sprout, Calendar } from 'lucide-react';

/** Whole days from an ISO date to today, or null for a missing or future date. */
function daysSince(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const start = new Date(iso).getTime();
  if (Number.isNaN(start)) return null;
  const days = Math.floor((Date.now() - start) / 86_400_000);
  return days >= 0 ? days : null;
}

export const FarmerDashboard: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  // Modals for Hero Launcher
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);

  // Live queries
  const { data: farmer, isLoading: isFarmerLoading } = useFarmerProfile();
  const { data: fields = [], isLoading: isFieldsLoading } = useFarmerFields(farmer?.id);
  const { fieldCrops } = useFarmerCrops();
  const { fieldCrop: primaryFieldCrop, cropName: primaryCrop } = usePrimaryFieldCrop();
  const sownDays = daysSince(primaryFieldCrop?.sowing_date);
  // The farmer's LGD district name (from the weather feed), not the village.
  const { data: feeds } = useQuery({ queryKey: ['govconnect', 'weather-feed'], queryFn: feedApi.weatherFeed });
  const feedDistrict = feeds?.[0]?.district_name ?? null;
  const { data: weather, isLoading: isWeatherLoading } = useCurrentWeather(
    farmer?.village || undefined,
  );
  const { data: forecast, isLoading: isForecastLoading } = useWeatherForecast(
    farmer?.village || undefined,
  );
  const { alerts, acknowledgeAlert, isAcknowledging } = useFarmerAlerts(farmer?.id);

  const currentDate = new Date().toLocaleDateString(i18n.language, {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  const handleHeroAction = (action: 'voice' | 'text' | 'vision') => {
    if (action === 'voice') {
      setIsVoiceOpen(true);
    } else if (action === 'vision') {
      // Photo checks run in the Ask chat, which asks the farmer to confirm the crop first (Phase 9).
      void navigate('/farmer/ask');
    } else {
      navigate('/farmer/ask');
    }
  };


  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner with Atmospheric Agricultural Background */}
      <section className="agri-hero-bg rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-primary-600/40">
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 max-w-xl">
            <div className="flex items-center gap-2 text-primary-200 text-caption font-medium">
              <Calendar className="w-3.5 h-3.5 text-primary-300" aria-hidden="true" />
              <span>{currentDate}</span>
            </div>
            <h1 className="text-display font-black tracking-tight text-white drop-shadow-sm">
              {farmer?.full_name ? t('farmer.dash.greeting', { name: farmer.full_name }) : t('farmer.dash.greetingNoName')}
            </h1>
            {(farmer?.village || feedDistrict) && (
              <p className="text-body text-primary-100/90 font-medium">
                {[farmer?.village, feedDistrict].filter(Boolean).join(', ')}
              </p>
            )}
          </div>

          {primaryFieldCrop && (
            <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
              <div className="inline-flex items-center gap-1.5 bg-white/15 backdrop-blur-md border border-white/25 px-3 py-1.5 rounded-full text-caption font-medium text-white shadow-sm">
                <Sprout className="w-3.5 h-3.5 text-primary-200" aria-hidden="true" />
                <span>
                  {[primaryCrop, primaryFieldCrop.season, primaryFieldCrop.year].filter(Boolean).join(' · ')}
                </span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Hero Multimodal Action Launcher */}
      <HeroActionGrid onSelectAction={handleHeroAction} />

      {/* Official Govt warnings (Govt Connect) */}
      <ActiveWarningsCard />

      {/* District weather feed, cross-checked against a second source */}
      <WeatherFeedCard />

      {/* Proactive Risk Alerts Banner (High Priority) */}
      <AlertBanner
        alerts={alerts}
        onAcknowledge={acknowledgeAlert}
        isAcknowledging={isAcknowledging}
      />

      {/* Farm Snapshot & Live Weather Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Farm Snapshot */}
        <FarmSummaryCard
          farmer={farmer}
          fields={fields}
          fieldCrops={fieldCrops}
          isLoading={isFarmerLoading || isFieldsLoading}
        />

        {/* Live Weather & Spray Advisory */}
        <WeatherWidget
          weather={weather}
          forecast={forecast}
          isLoading={isWeatherLoading || isForecastLoading}
        />
      </div>

      {/* Market & Crop Progression Snapshot */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Official mandi price + 30-day trend (AGMARKNET) */}
        <MandiTrendCard crop={primaryCrop} district={feedDistrict} />

        {/* The farmer's recorded crop: only what is in their field records */}
        <Card variant="raised" padding="md" className="space-y-2" data-testid="my-crop-card">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">{t('farmer.dash.myCrop')}</span>
              <div className="w-8 h-8 rounded-lg bg-success-50 text-success-600 flex items-center justify-center">
                <Sprout className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text">
              {primaryCrop ?? t('farmer.dash.noCrop')}
            </CardTitle>
            {primaryFieldCrop && (
              <p className="text-caption text-text-secondary">
                {[primaryFieldCrop.season, primaryFieldCrop.year, t(`farmer.dash.status.${primaryFieldCrop.status}`, { defaultValue: primaryFieldCrop.status })]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            )}
          </CardHeader>
          <CardContent className="pt-2 border-t border-border text-caption">
            {!primaryFieldCrop ? (
              <span className="text-text-muted">{t('farmer.dash.cropHelp')}</span>
            ) : sownDays !== null ? (
              <span className="text-text">{t('farmer.dash.daysSinceSowing', { count: sownDays })}</span>
            ) : (
              <span className="text-text-muted">{t('farmer.dash.noSowingDate')}</span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Modals for Voice and Vision */}
      <VoiceRecorderModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        defaultLanguage="te"
      />
    </div>
  );
};

export default FarmerDashboard;
