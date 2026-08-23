/**
 * Authentication API service.
 *
 * Wraps the backend auth endpoints: login, refresh, logout.
 */

import { apiClient, setAccessToken, setRefreshToken, clearTokens, getRefreshToken } from './client';
import type { LoginRequest, TokenResponse } from '@/types/auth';

/**
 * Authenticate with phone/email + password.
 * Stores tokens in memory/localStorage on success.
 */
export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const data = await apiClient.post<TokenResponse>('/auth/login', credentials, {
    skipAuth: true,
  });
  setAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Exchange a refresh token for a new token pair.
 * Called automatically by the API client on 401, but can also be called manually.
 */
export async function refreshTokens(): Promise<TokenResponse | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const data = await apiClient.post<TokenResponse>(
      '/auth/refresh',
      { refresh_token: refreshToken },
      { skipAuth: true },
    );
    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return data;
  } catch {
    clearTokens();
    return null;
  }
}

/**
 * Revoke the current refresh token and clear all local tokens.
 */
export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await apiClient.post('/auth/logout', { refresh_token: refreshToken }, { skipAuth: true });
    } catch {
      // Best-effort — clear tokens regardless
    }
  }
  clearTokens();
}
