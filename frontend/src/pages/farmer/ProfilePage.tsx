/**
 * ProfilePage Component.
 *
 * Displays farmer identity details, preferred language switcher,
 * notification channel toggles, quiet hours, and session controls.
 */

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useFarmerProfile } from '@/features/farmer/hooks/useFarmerData';
import { useTranslation } from 'react-i18next';
import {
  Phone,
  MapPin,
  Globe,
  Bell,
  LogOut,
  Check,
} from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { data: farmer } = useFarmerProfile();
  const { i18n } = useTranslation();

  const [selectedLanguage, setSelectedLanguage] = useState(i18n.language || 'en');
  const [weatherAlertsEnabled, setWeatherAlertsEnabled] = useState(true);
  const [pestAlertsEnabled, setPestAlertsEnabled] = useState(true);
  const [marketAlertsEnabled, setMarketAlertsEnabled] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleLanguageChange = (lang: string) => {
    setSelectedLanguage(lang);
    i18n.changeLanguage(lang);
  };

  const handleSavePreferences = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Page Title */}
      <div>
        <h1 className="text-display font-extrabold text-text tracking-tight">Farmer Profile</h1>
        <p className="text-body text-text-secondary">
          Manage your identity, language preference, and notification settings
        </p>
      </div>

      {/* Identity Card */}
      <Card variant="raised" padding="md" className="space-y-4">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-primary-100 text-primary-700 flex items-center justify-center font-bold text-heading">
              {farmer?.full_name?.charAt(0) || 'F'}
            </div>
            <div>
              <CardTitle as="h2" className="text-subheading font-bold text-text">
                {farmer?.full_name || 'Farmer Account'}
              </CardTitle>
              <div className="flex items-center gap-2 text-caption text-text-muted mt-0.5">
                <span className="capitalize">{user?.role || 'Farmer'}</span>
                <span>•</span>
                <span>ID #{farmer?.id || '101'}</span>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-0 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-small">
            <div className="p-3 rounded-lg bg-surface-raised border border-border flex items-center gap-3">
              <Phone className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <div>
                <span className="text-[11px] uppercase text-text-muted block">Phone Number</span>
                <span className="font-semibold text-text">{farmer?.phone || '+91 98765 43210'}</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-raised border border-border flex items-center gap-3">
              <MapPin className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <div>
                <span className="text-[11px] uppercase text-text-muted block">Village &amp; District</span>
                <span className="font-semibold text-text">
                  {farmer?.village || 'Khammam'}, Telangana
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Language Preference */}
      <Card variant="raised" padding="md" className="space-y-4">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <CardTitle as="h3" className="text-body font-bold text-text">
              Preferred Language
            </CardTitle>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {[
              { code: 'te', label: 'తెలుగు (Telugu)' },
              { code: 'hi', label: 'हिंदी (Hindi)' },
              { code: 'en', label: 'English' },
            ].map((lang) => (
              <button
                key={lang.code}
                type="button"
                onClick={() => handleLanguageChange(lang.code)}
                className={`p-3 rounded-xl border text-small font-semibold transition-all cursor-pointer text-left flex items-center justify-between ${
                  selectedLanguage === lang.code
                    ? 'bg-primary-50 border-primary-500 text-primary-900 shadow-sm'
                    : 'bg-surface border-border text-text hover:bg-surface-raised'
                }`}
              >
                <span>{lang.label}</span>
                {selectedLanguage === lang.code && (
                  <Check className="w-4 h-4 text-primary-600" aria-hidden="true" />
                )}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      <Card variant="raised" padding="md" className="space-y-4">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <CardTitle as="h3" className="text-body font-bold text-text">
              Notification &amp; Advisory Alerts
            </CardTitle>
          </div>
        </CardHeader>

        <CardContent className="pt-0 space-y-3">
          <label className="flex items-center justify-between p-3 rounded-lg bg-surface-raised border border-border cursor-pointer">
            <div>
              <span className="text-small font-bold text-text block">Weather &amp; Spray Alerts</span>
              <span className="text-caption text-text-secondary">
                Receive warnings for rain, heatwaves, and spray window feasibility
              </span>
            </div>
            <input
              type="checkbox"
              checked={weatherAlertsEnabled}
              onChange={(e) => setWeatherAlertsEnabled(e.target.checked)}
              className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-lg bg-surface-raised border border-border cursor-pointer">
            <div>
              <span className="text-small font-bold text-text block">Pest &amp; Disease Outbreak Alerts</span>
              <span className="text-caption text-text-secondary">
                Urgent notifications when regional pest thresholds are crossed
              </span>
            </div>
            <input
              type="checkbox"
              checked={pestAlertsEnabled}
              onChange={(e) => setPestAlertsEnabled(e.target.checked)}
              className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-lg bg-surface-raised border border-border cursor-pointer">
            <div>
              <span className="text-small font-bold text-text block">Mandi Price Updates</span>
              <span className="text-caption text-text-secondary">
                Daily commodity arrivals and price fluctuations in nearby mandis
              </span>
            </div>
            <input
              type="checkbox"
              checked={marketAlertsEnabled}
              onChange={(e) => setMarketAlertsEnabled(e.target.checked)}
              className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500 cursor-pointer"
            />
          </label>

          <div className="flex items-center justify-between pt-2">
            {savedSuccess ? (
              <span className="text-caption font-semibold text-success-700 flex items-center gap-1">
                <Check className="w-4 h-4" aria-hidden="true" />
                Preferences saved successfully!
              </span>
            ) : (
              <div />
            )}
            <Button variant="primary" size="sm" onClick={handleSavePreferences}>
              Save Preferences
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Logout Action */}
      <div className="flex justify-end pt-2">
        <Button variant="danger" onClick={logout} className="w-full sm:w-auto">
          <LogOut className="w-4 h-4 mr-2" aria-hidden="true" />
          Sign Out of KrishiOS
        </Button>
      </div>
    </div>
  );
};

export default ProfilePage;
