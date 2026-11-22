/**
 * Whether a backend capability (weather, advisory, ...) is served by a live source, from
 * GET /providers. Fails closed: while loading, on error, or for a mock/sandbox source it is
 * false, so placeholder data is never shown to farmers as real.
 */

import { useQuery } from '@tanstack/react-query';

import { getProviders } from '@/services/api/providers';

export function useLiveProvider(capability: string): { isLive: boolean; isLoading: boolean } {
  const providers = useQuery({ queryKey: ['providers'], queryFn: getProviders, staleTime: 10 * 60 * 1000 });
  const entry = providers.data?.providers.find((p) => p.capability === capability);
  return { isLive: entry?.kind === 'live', isLoading: providers.isLoading };
}
