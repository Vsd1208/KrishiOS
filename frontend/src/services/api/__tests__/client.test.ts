import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, setAccessToken, clearTokens } from '../client';
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
});
