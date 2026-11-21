/** useLiveProvider fails closed: only a live source counts, never a mock, a sandbox or an error. */

import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import * as providersApi from '@/services/api/providers';
import { useLiveProvider } from '../hooks/useLiveProvider';

const Probe: React.FC<{ capability: string }> = ({ capability }) => {
  const { isLive, isLoading } = useLiveProvider(capability);
  return <p>{isLoading ? 'loading' : isLive ? 'live' : 'not live'}</p>;
};

const show = (capability: string) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <Probe capability={capability} />
    </QueryClientProvider>,
  );

const entry = (capability: string, kind: string) => ({
  capability, configured: kind, name: kind, version: '1', kind,
  sends_data_off_device: false, description: null, error: null,
});

describe('useLiveProvider', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('is false for a mock weather source and true for a live one', async () => {
    vi.spyOn(providersApi, 'getProviders').mockResolvedValue({
      providers: [entry('weather', 'mock'), entry('market', 'live')],
      policy_violations: [],
    } as Awaited<ReturnType<typeof providersApi.getProviders>>);
    show('weather');
    expect(await screen.findByText('not live')).toBeInTheDocument();
  });

  it('is true for a live source', async () => {
    vi.spyOn(providersApi, 'getProviders').mockResolvedValue({
      providers: [entry('weather', 'live')],
      policy_violations: [],
    } as Awaited<ReturnType<typeof providersApi.getProviders>>);
    show('weather');
    expect(await screen.findByText('live')).toBeInTheDocument();
  });

  it('is false when the provider list cannot be loaded', async () => {
    vi.spyOn(providersApi, 'getProviders').mockRejectedValue(new Error('down'));
    show('weather');
    expect(await screen.findByText('not live')).toBeInTheDocument();
  });
});
