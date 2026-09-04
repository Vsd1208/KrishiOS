/**
 * FarmerDashboard Page.
 *
 * Agricultural intelligence overview and primary entry point for farmers.
 * Combines farm summary, hero multimodal ask launcher, live weather & spray window,
 * and proactive crop risk alerts.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import {
  useFarmerProfile,
  useFarmerFields,
  useFarmerCrops,
  useCurrentWeather,
  useWeatherForecast,
  useFarmerAlerts,
  useMarketPrices,
} from '@/features/farmer/hooks/useFarmerData';
import { FarmSummaryCard } from '@/features/farmer/components/FarmSummaryCard';
import { WeatherWidget } from '@/features/farmer/components/WeatherWidget';
import { HeroActionGrid } from '@/features/farmer/components/HeroActionGrid';
import { AlertBanner } from '@/features/farmer/components/AlertBanner';
import { VoiceRecorderModal } from '@/features/farmer/components/VoiceRecorderModal';
import { CropVisionModal } from '@/features/farmer/components/CropVisionModal';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { TrendingUp, Sprout, Calendar } from 'lucide-react';

export const FarmerDashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Modals for Hero Launcher
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [isVisionOpen, setIsVisionOpen] = useState(false);

  // Live queries
  const { data: farmer, isLoading: isFarmerLoading } = useFarmerProfile();
  const { data: fields = [], isLoading: isFieldsLoading } = useFarmerFields(farmer?.id);
  const { fieldCrops } = useFarmerCrops();
  const { data: weather, isLoading: isWeatherLoading } = useCurrentWeather(
    farmer?.village || 'Khammam',
  );
  const { data: forecast, isLoading: isForecastLoading } = useWeatherForecast(
    farmer?.village || 'Khammam',
  );
  const { alerts, acknowledgeAlert, isAcknowledging } = useFarmerAlerts(farmer?.id);
  const { data: mandiPrices } = useMarketPrices('Paddy', farmer?.village || 'Khammam');

  const currentDate = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  const handleHeroAction = (action: 'voice' | 'text' | 'vision') => {
    if (action === 'voice') {
      setIsVoiceOpen(true);
    } else if (action === 'vision') {
      setIsVisionOpen(true);
    } else {
      navigate('/farmer/ask');
    }
  };

  const primaryMandiPrice = mandiPrices?.[0];

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
              Namaste, {farmer?.full_name || 'Farmer'}
            </h1>
            <p className="text-body text-primary-100/90 font-medium">
              KrishiOS Agricultural Decision Support • {farmer?.village ? `${farmer.village}, Telangana` : 'Telangana Region'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
            <div className="inline-flex items-center gap-2 bg-primary-950/70 backdrop-blur-md border border-primary-400/40 px-3.5 py-1.5 rounded-full text-caption font-semibold text-primary-100 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" aria-hidden="true" />
              <span>Active Kharif Season • {user?.role || 'Farmer'}</span>
            </div>
            <div className="inline-flex items-center gap-1.5 bg-white/15 backdrop-blur-md border border-white/25 px-3 py-1.5 rounded-full text-caption font-medium text-white shadow-sm">
              <Sprout className="w-3.5 h-3.5 text-primary-200" aria-hidden="true" />
              <span>{fieldCrops?.[0] ? 'Standing Crop' : 'Active Landholding'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Hero Multimodal Action Launcher */}
      <HeroActionGrid onSelectAction={handleHeroAction} />

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
        {/* Mandi Rate Snapshot */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Mandi Benchmark Price
              </span>
              <div className="w-8 h-8 rounded-lg bg-info-50 text-info-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text">
              {primaryMandiPrice
                ? `₹${primaryMandiPrice.modal_price_inr_quintal} / qtl`
                : '₹2,320 / qtl'}
            </CardTitle>
            <p className="text-caption text-text-secondary">
              {primaryMandiPrice
                ? `${primaryMandiPrice.commodity} (${primaryMandiPrice.variety}) • ${primaryMandiPrice.market}`
                : 'Paddy Common • Warangal Mandi'}
            </p>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border">
            <div className="flex items-center justify-between text-caption">
              <span className="text-success-700 font-semibold">+2.4% vs last week</span>
              <span className="text-text-muted">MSP: ₹2,183 / qtl</span>
            </div>
          </CardContent>
        </Card>

        {/* Crop Stage Snapshot */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Crop Growth Phase
              </span>
              <div className="w-8 h-8 rounded-lg bg-success-50 text-success-600 flex items-center justify-center">
                <Sprout className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text">
              Tillering Stage
            </CardTitle>
            <p className="text-caption text-text-secondary">Paddy • Day 42 of 120 (Optimal Health)</p>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border">
            <div className="flex items-center justify-between text-caption">
              <span className="text-primary-700 font-semibold">Nitrogen top-dressing recommended</span>
              <span className="text-text-muted">Next: Panicle Initiation</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Modals for Voice and Vision */}
      <VoiceRecorderModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        defaultLanguage="te"
      />
      <CropVisionModal
        isOpen={isVisionOpen}
        onClose={() => setIsVisionOpen(false)}
        defaultCrop="Paddy"
      />
    </div>
  );
};

export default FarmerDashboard;
