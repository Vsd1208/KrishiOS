import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '../AuthContext';
import * as authService from '@/services/api/auth';
import { clearTokens } from '@/services/api/client';

describe('AuthContext', () => {
  beforeEach(() => {
    clearTokens();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it('initializes with unauthenticated state when no tokens exist', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it('updates state on successful login', async () => {
    // Generate valid base64 payload for JWT: sub=uuid, role=farmer, permissions=[]
    const payload = {
      sub: '550e8400-e29b-41d4-a716-446655440000',
      role: 'farmer',
      permissions: ['farmer:read', 'weather:read'],
      jti: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 900,
    };
    const encodedPayload = btoa(JSON.stringify(payload));
    const mockJwt = `header.${encodedPayload}.signature`;

    vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: mockJwt,
      refresh_token: 'mock-refresh-token',
      token_type: 'Bearer',
      expires_in: 900,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.login({ phone: '9876543210', password: 'secretpassword' });
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.role).toBe('farmer');
    expect(result.current.user?.uuid).toBe('550e8400-e29b-41d4-a716-446655440000');
  });

  it('clears state on logout', async () => {
    vi.spyOn(authService, 'logout').mockResolvedValue();

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });
});
