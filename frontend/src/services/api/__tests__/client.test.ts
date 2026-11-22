import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, setAccessToken, setRefreshToken, clearTokens, refreshSession } from '../client';
import { ApiError } from '@/types/api';

describe('API Client', () => {
  beforeEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  it('attaches Authorization Bearer header when access token exists', async () => {
    setAccessToken('mock-access-token');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiClient.get<{ success: boolean }>('/health');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer mock-access-token',
        }),
      }),
    );
    expect(result).toEqual({ success: true });
  });

  it('parses standardized backend error response into ApiError', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: 'entity_not_found',
          message: 'Farmer not found',
        },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiClient.get('/farmers/999')).rejects.toThrow(ApiError);
    await expect(apiClient.get('/farmers/999')).rejects.toMatchObject({
      status: 404,
      code: 'entity_not_found',
      message: 'Farmer not found',
    });
  });

  it('handles 204 No Content responses cleanly', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => null,
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiClient.delete('/farmers/1');
    expect(result).toBeUndefined();
  });

  it('runs one refresh for parallel callers (refresh tokens rotate)', async () => {
    setRefreshToken('r1');
    let resolve!: (v: unknown) => void;
    const fetchMock = vi.fn().mockReturnValue(new Promise((r) => { resolve = r; }));
    vi.stubGlobal('fetch', fetchMock);

    const a = refreshSession();
    const b = refreshSession();
    resolve({ ok: true, status: 200, json: async () => ({ access_token: 'a2', refresh_token: 'r2' }) });

    expect(await a).toEqual(await b);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('retries a request only once after a 401', async () => {
    setAccessToken('a1');
    setRefreshToken('r1');
    const fetchMock = vi.fn(async (url: string) =>
      String(url).includes('/auth/refresh')
        ? { ok: true, status: 200, json: async () => ({ access_token: 'a2', refresh_token: 'r2' }) }
        : { ok: false, status: 401, json: async () => null },
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiClient.get('/farmers/me')).rejects.toMatchObject({ status: 401 });
    const calls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(calls.filter((u) => u.includes('/auth/refresh'))).toHaveLength(1);
    expect(calls.filter((u) => u.includes('/farmers/me'))).toHaveLength(2);
  });
});
