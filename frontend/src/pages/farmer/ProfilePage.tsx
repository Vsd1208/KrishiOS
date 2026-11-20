/**
 * ProfilePage: the signed-in farmer's own details, language and alert choices.
 *
 * The language choice is saved to the farmer profile (the bot and SMS use it). The alert switches
 * are saved to the notification preferences the alert service reads. Nothing shows "saved" unless
 * the server confirmed it, and missing details show a dash, never a sample value.
 */

import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Phone, MapPin, Globe, Bell, LogOut, Check, AlertCircle } from 'lucide-react';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { FARMER_QUERY_KEYS, useFarmerProfile } from '@/features/farmer/hooks/useFarmerData';
import { LocationsCard } from '@/features/govconnect/LocationsCard';
import { PushOptIn } from '@/features/govconnect/PushOptIn';
import { alertsApi } from '@/services/api/alerts';
import { farmerApi } from '@/services/api/farmer';
import type { NotificationPreference } from '@/types/proactive';

const LANGUAGES = [
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'hi', label: 'हिंदी (Hindi)' },
  { code: 'en', label: 'English' },
] as const;

type AlertKey = 'enable_weather_alerts' | 'enable_disease_alerts' | 'enable_market_alerts' | 'enable_scheme_alerts';
const ALERTS: { key: AlertKey; id: string }[] = [
  { key: 'enable_weather_alerts', id: 'weather' },
  { key: 'enable_disease_alerts', id: 'disease' },
  { key: 'enable_market_alerts', id: 'market' },
  { key: 'enable_scheme_alerts', id: 'scheme' },
];

export const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { data: farmer, isLoading } = useFarmerProfile();
  const current = (i18n.language || 'en').slice(0, 2);

  const prefs = useQuery({
    queryKey: FARMER_QUERY_KEYS.preferences(farmer?.id),
    queryFn: () => alertsApi.getPreferences(),
    enabled: Boolean(farmer),
  });
  const [draft, setDraft] = useState<Record<AlertKey, boolean> | null>(null);
  useEffect(() => {
    if (prefs.data) {
      setDraft({
        enable_weather_alerts: prefs.data.enable_weather_alerts,
        enable_disease_alerts: prefs.data.enable_disease_alerts,
        enable_market_alerts: prefs.data.enable_market_alerts,
        enable_scheme_alerts: prefs.data.enable_scheme_alerts,
      });
    }
  }, [prefs.data]);

  const saveLanguage = useMutation({
    mutationFn: (lang: string) => farmerApi.updateFarmer(farmer!.id, { preferred_language: lang }),
    onSuccess: (updated) => qc.setQueryData(FARMER_QUERY_KEYS.me, updated),
  });
  const savePrefs = useMutation({
    mutationFn: (p: NotificationPreference) => {
      // The endpoint replaces the whole record, so send every field, not only the switches.
      const { id: _id, farmer_id: _fid, created_at: _c, updated_at: _u, ...rest } = p;
      return alertsApi.updatePreferences({ ...rest, ...draft });
    },
    onSuccess: (saved) => qc.setQueryData(FARMER_QUERY_KEYS.preferences(farmer?.id), saved),
  });

  const chooseLanguage = (code: string) => {
    void i18n.changeLanguage(code);
    if (farmer) saveLanguage.mutate(code);
  };
  const dirty =
    draft !== null && prefs.data !== undefined && ALERTS.some((a) => draft[a.key] !== prefs.data[a.key]);

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-display font-extrabold text-text tracking-tight">{t('profile.title')}</h1>
        <p className="text-body text-text-secondary">{t('profile.subtitle')}</p>
      </div>

      <Card variant="raised" padding="md" className="space-y-4">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl bg-primary-100 text-primary-700 flex items-center justify-center font-bold text-heading"
              aria-hidden="true"
            >
              {farmer?.full_name?.charAt(0) || '?'}
            </div>
            <div className="min-w-0">
              <CardTitle as="h2" className="text-subheading font-bold text-text break-words">
                {farmer?.full_name || (isLoading ? t('common.loading') : t('profile.noProfile'))}
              </CardTitle>
              {user?.role && (
                <p className="text-caption text-text-muted mt-0.5">{t(`roles.${user.role}`, { defaultValue: user.role })}</p>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-small">
            <div className="p-3 rounded-lg bg-surface-raised border border-border flex items-center gap-3">
              <Phone className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                <span className="text-[11px] uppercase text-text-muted block">{t('auth.phone')}</span>
                <span className="font-semibold text-text break-all">{farmer?.phone || '—'}</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface-raised border border-border flex items-center gap-3">
              <MapPin className="w-4 h-4 text-primary-600 flex-shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                <span className="text-[11px] uppercase text-text-muted block">{t('profile.village')}</span>
                <span className="font-semibold text-text break-words">{farmer?.village || '—'}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card variant="raised" padding="md" className="space-y-4">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <CardTitle as="h3" className="text-body font-bold text-text">
              {t('profile.language')}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-0 space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2" role="radiogroup" aria-label={t('profile.language')}>
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                role="radio"
                aria-checked={current === lang.code}
                onClick={() => chooseLanguage(lang.code)}
                disabled={saveLanguage.isPending}
                className={`p-3 rounded-xl border text-small font-semibold transition-all cursor-pointer text-left flex items-center justify-between disabled:opacity-60 ${
                  current === lang.code
                    ? 'bg-primary-50 border-primary-500 text-primary-900 shadow-sm'
                    : 'bg-surface border-border text-text hover:bg-surface-raised'
                }`}
              >
                <span>{lang.label}</span>
                {current === lang.code && <Check className="w-4 h-4 text-primary-600" aria-hidden="true" />}
              </button>
            ))}
          </div>
          <p className="text-caption" aria-live="polite">
            {saveLanguage.isSuccess && <span className="text-success-700">{t('profile.languageSaved')}</span>}
            {saveLanguage.isError && <span className="text-danger-700">{t('profile.saveFailed')}</span>}
            {!farmer && !isLoading && <span className="text-text-muted">{t('profile.languageLocalOnly')}</span>}
          </p>
        </CardContent>
      </Card>

      {farmer && (
        <Card variant="raised" padding="md" className="space-y-4">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary-600" aria-hidden="true" />
              <CardTitle as="h3" className="text-body font-bold text-text">
                {t('profile.alertsTitle')}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-0 space-y-3">
            {prefs.isError ? (
              <p className="text-caption text-danger-700 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" aria-hidden="true" />
                {t('profile.prefsFailed')}
              </p>
            ) : !draft ? (
              <p className="text-caption text-text-muted">{t('common.loading')}</p>
            ) : (
              <>
                {ALERTS.map((a) => (
                  <label
                    key={a.key}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg bg-surface-raised border border-border cursor-pointer"
                  >
                    <div>
                      <span className="text-small font-bold text-text block">{t(`profile.alerts.${a.id}`)}</span>
                      <span className="text-caption text-text-secondary">{t(`profile.alerts.${a.id}Help`)}</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={draft[a.key]}
                      onChange={(e) => setDraft({ ...draft, [a.key]: e.target.checked })}
                      className="w-5 h-5 shrink-0 rounded text-primary-600 focus:ring-primary-500 cursor-pointer"
                    />
                  </label>
                ))}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                  <span className="text-caption font-semibold" aria-live="polite">
                    {savePrefs.isSuccess && !dirty && (
                      <span className="text-success-700 flex items-center gap-1">
                        <Check className="w-4 h-4" aria-hidden="true" />
                        {t('profile.saved')}
                      </span>
                    )}
                    {savePrefs.isError && <span className="text-danger-700">{t('profile.saveFailed')}</span>}
                  </span>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!dirty || savePrefs.isPending}
                    onClick={() => prefs.data && savePrefs.mutate(prefs.data)}
                  >
                    {savePrefs.isPending ? t('profile.saving') : t('profile.save')}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      <LocationsCard />

      <PushOptIn />

      <div className="flex justify-end pt-2">
        <Button variant="danger" onClick={logout} className="w-full sm:w-auto">
          <LogOut className="w-4 h-4 mr-2" aria-hidden="true" />
          {t('auth.logout')}
        </Button>
      </div>
    </div>
  );
};

export default ProfilePage;
