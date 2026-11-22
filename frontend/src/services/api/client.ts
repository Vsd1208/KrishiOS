/**
 * Centralized API client for KrishiOS.
 *
 * Architecture:
 *   Component → Feature API (services/api/auth.ts, etc.) → this client → Backend
 *
 * Responsibilities:
 *   - Base URL management
 *   - Authorization header injection
 *   - Automatic token refresh on 401
 *   - Standardized error parsing into ApiError
 *   - Request timeout (30s default)
 *   - JSON serialization/deserialization
 *
 * Components must NEVER call fetch() directly.
 */

import { config } from '@/app/config';
import { ApiError } from '@/types/api';
import type { ApiErrorResponse } from '@/types/api';
import type { TokenResponse } from '@/types/auth';

// ── Token Storage ────────────────────────────────────────────────────────────
// Access token kept in memory (never persisted).
// Refresh token in localStorage (single-use with rotation, acceptable risk).

let accessToken: string | null = null;

const REFRESH_TOKEN_KEY = 'krishios_refresh_token';

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ── Refresh Lock ─────────────────────────────────────────────────────────────
// One refresh at a time for the whole app: session restore on page load and every 401 retry
// share it. Refresh tokens rotate, so parallel refreshes would each mint a new token (and the
// losers could log the user out).

let refreshPromise: Promise<TokenResponse | null> | null = null;

/** Exchange the refresh token for new tokens, joining a refresh already in flight. */
export function refreshSession(): Promise<TokenResponse | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return Promise.resolve(null);

  // If a refresh is already in progress, wait for it
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = (await response.json()) as TokenResponse;
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      return data;
    } catch {
      clearTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function attemptTokenRefresh(): Promise<boolean> {
  return (await refreshSession()) !== null;
}

// ── Core Request Function ────────────────────────────────────────────────────

const DEFAULT_TIMEOUT_MS = 30_000;

interface RequestOptions {
  /** Skip adding the Authorization header (used for login/refresh). */
  skipAuth?: boolean;
  /** Request timeout in milliseconds. Defaults to 30s. */
  timeout?: number;
  /** Additional headers. */
  headers?: Record<string, string>;
  /** Internal: this is the single retry after a 401. */
  isRetry?: boolean;
}

/**
 * Make an authenticated API request.
 *
 * - Prepends the base URL
 * - Attaches Bearer token
 * - Parses the backend's standard error envelope
 * - Retries once on 401 after refreshing the token
 */
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const { skipAuth = false, timeout = DEFAULT_TIMEOUT_MS, headers: extraHeaders, isRetry = false } = options;

  // On page load the access token arrives with the session refresh; wait instead of sending a
  // request that is bound to fail with 401 and start another refresh.
  if (!skipAuth && !accessToken && refreshPromise) await refreshPromise;
  const sentToken = skipAuth ? null : accessToken;

  const url = `${config.apiBaseUrl}${path}`;

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...extraHeaders,
  };

  if (!skipAuth && accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(408, 'timeout', 'Request timed out. Please try again.');
    }
    throw new ApiError(0, 'network_error', 'Unable to reach KrishiOS. Please check your connection.');
  } finally {
    clearTimeout(timeoutId);
  }

  // ── Handle 401 with automatic refresh ────────────────────────────────────
  if (response.status === 401 && !skipAuth && !isRetry) {
    // Another request may already have refreshed; then just retry with the newer token.
    const refreshed = (accessToken !== null && accessToken !== sentToken) || (await attemptTokenRefresh());
    if (refreshed) {
      // Retry the original request once with the new token
      return request<T>(method, path, body, { ...options, skipAuth: false, isRetry: true });
    }
    // Refresh failed — throw so AuthContext can redirect to login
    throw new ApiError(401, 'unauthorized', 'Session expired. Please log in again.');
  }

  // ── Handle 204 No Content ────────────────────────────────────────────────
  if (response.status === 204) {
    return undefined as T;
  }

  // ── Parse response body ──────────────────────────────────────────────────
  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = data as ApiErrorResponse | null;
    // Some endpoints return a structured detail ({message, reasons}); flatten it for display.
    const raw: unknown = errorBody?.error?.message;
    const structured = raw as { message?: string; reasons?: string[] } | null;
    const message =
      typeof raw === 'string'
        ? raw
        : structured && typeof structured === 'object' && structured.message
          ? [structured.message, ...(structured.reasons ?? [])].join(' — ')
          : `Request failed with status ${response.status}`;
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? 'unknown_error',
      message,
      errorBody?.error?.details,
    );
  }

  return data as T;
}

// ── Public API ───────────────────────────────────────────────────────────────

export const apiClient = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('GET', path, undefined, options);
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, body, options);
  },

  postForm<T>(path: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, formData, options);
  },

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, body, options);
  },

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PUT', path, body, options);
  },

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('DELETE', path, undefined, options);
  },
};
