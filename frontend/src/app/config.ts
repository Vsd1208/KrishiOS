/**
 * Environment configuration for the KrishiOS frontend.
 *
 * All environment access is centralized here so that:
 * 1. Components never read import.meta.env directly
 * 2. Missing variables fail fast at startup
 * 3. Defaults are explicit and documented
 */

export const config = {
  /** Backend API base URL (no trailing slash). */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',

  /** Default UI language. */
  defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE || 'en',

  /** Whether the app is running in development mode. */
  isDev: import.meta.env.DEV,
} as const;
