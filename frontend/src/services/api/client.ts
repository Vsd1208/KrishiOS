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
// Prevents multiple concurrent refresh requests when several 401s arrive.

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

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
        return false;
      }

      const data = (await response.json()) as TokenResponse;
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
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
  const { skipAuth = false, timeout = DEFAULT_TIMEOUT_MS, headers: extraHeaders } = options;

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
  if (response.status === 401 && !skipAuth) {
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      // Retry the original request with the new token
      return request<T>(method, path, body, { ...options, skipAuth: false });
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
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? 'unknown_error',
      errorBody?.error?.message ?? `Request failed with status ${response.status}`,
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
