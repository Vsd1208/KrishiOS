/**
 * FarmerDashboard Page.
 *
 * Agricultural intelligence overview and primary entry point for farmers.
 */

import React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import {
  Sun,
  CloudRain,
  Sprout,
  TrendingUp,
  AlertTriangle,
  MapPin,
  Calendar,
} from 'lucide-react';

export const FarmerDashboard: React.FC = () => {
  const { user } = useAuth();

  const currentDate = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <section className="bg-gradient-to-r from-primary-700 to-primary-600 rounded-xl p-6 text-white shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-primary-100 text-small">
              <Calendar className="w-4 h-4" aria-hidden="true" />
              <span>{currentDate}</span>
            </div>
            <h1 className="text-display font-bold tracking-tight">Welcome to KrishiOS</h1>
            <p className="text-body text-primary-100">
              Your agricultural intelligence dashboard
            </p>
          </div>
          <div className="inline-flex items-center gap-2 bg-primary-800/60 backdrop-blur-sm border border-primary-400/30 px-3.5 py-1.5 rounded-lg text-small">
            <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse" aria-hidden="true" />
            <span>Role: <strong className="capitalize">{user?.role || 'Farmer'}</strong></span>
          </div>
        </div>
      </section>

      {/* Quick Overview Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Weather Intelligence Card */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Weather Advisory</span>
              <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center">
                <Sun className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              31°C
            </CardTitle>
            <CardDescription>Partly Cloudy • 15% rain chance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border">
            <div className="flex items-center gap-1.5 text-text-secondary">
              <CloudRain className="w-3.5 h-3.5 text-info-600" aria-hidden="true" />
              <span>Light showers expected in 48 hours</span>
            </div>
          </CardContent>
        </Card>

        {/* Crop Health Card */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Active Crops</span>
              <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center">
                <Sprout className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              2 Fields
            </CardTitle>
            <CardDescription>Paddy (Kharif) &amp; Cotton</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border">
            <div className="flex items-center gap-1.5 text-success-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-success-500" aria-hidden="true" />
              <span>Optimal vegetative growth stage</span>
            </div>
          </CardContent>
        </Card>

        {/* Market Intelligence Card */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Mandi Prices</span>
              <div className="w-8 h-8 rounded-lg bg-info-50 text-info-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              ₹2,320 / qtl
            </CardTitle>
            <CardDescription>Paddy Grade A • Warangal Mandi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border">
            <span className="text-success-600 font-medium">+2.4% vs last week</span>
          </CardContent>
        </Card>

        {/* Active Alerts Card */}
        <Card variant="raised" padding="md" className="space-y-2">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Advisory Alerts</span>
              <div className="w-8 h-8 rounded-lg bg-danger-50 text-danger-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              1 Alert
            </CardTitle>
            <CardDescription>Stem Borer risk detected in region</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border">
            <span className="text-danger-600 font-medium">Action recommended by Agronomist</span>
          </CardContent>
        </Card>
      </div>

      {/* Field Overview Section */}
      <section className="space-y-4">
        <h2 className="text-subheading font-semibold text-text">Registered Plots</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card variant="default" padding="md" className="hover:border-primary-300 transition-colors">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-text-secondary text-small">
                  <MapPin className="w-4 h-4 text-primary-600" aria-hidden="true" />
                  <span>North Field — Plot #1</span>
                </div>
                <h3 className="text-subheading font-semibold text-text">Paddy (BPT 5204)</h3>
                <p className="text-small text-text-secondary">3.5 Acres • Sown: 42 days ago</p>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-caption font-semibold bg-success-50 text-success-700 border border-success-200">
                Healthy
              </span>
            </div>
          </Card>

          <Card variant="default" padding="md" className="hover:border-primary-300 transition-colors">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-text-secondary text-small">
                  <MapPin className="w-4 h-4 text-primary-600" aria-hidden="true" />
                  <span>South Field — Plot #2</span>
                </div>
                <h3 className="text-subheading font-semibold text-text">Cotton (Bt)</h3>
                <p className="text-small text-text-secondary">2.0 Acres • Sown: 28 days ago</p>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-caption font-semibold bg-warning-50 text-warning-700 border border-warning-200">
                Advisory Needed
              </span>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default FarmerDashboard;
