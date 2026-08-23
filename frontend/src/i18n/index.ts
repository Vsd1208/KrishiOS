import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import enCommon from './locales/en/common.json';
import teCommon from './locales/te/common.json';
import hiCommon from './locales/hi/common.json';

export const defaultNS = 'common';

export const resources = {
  en: {
    common: enCommon,
  },
  te: {
    common: teCommon,
  },
  hi: {
    common: hiCommon,
  },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: ['en', 'te', 'hi'],
    defaultNS: 'common',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
    resources,
  });

export default i18n;
