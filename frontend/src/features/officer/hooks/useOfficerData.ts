/**
 * Custom React Query hooks for Agricultural Officer Console.
 *
 * Integrates:
 * - Pending Human-in-the-Loop review queue & actions
 * - District farmers directory & field landholdings
 * - Knowledge graph candidate relationship verification
 * - Regional proactive decisions & severe weather monitoring
 * - Outbreak & regional advisory event ingestion
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { officerApi } from '@/services/api/officer';
import { reviewsApi } from '@/services/api/reviews';
import { farmerApi } from '@/services/api/farmer';
import { graphApi } from '@/services/api/graph';
import { alertsApi } from '@/services/api/alerts';
import { weatherApi } from '@/services/api/weather';
import { eventsApi } from '@/services/api/events';
import type { OfficerReviewActionRequest, ReviewCandidateRequest, EventIngestRequest } from '@/types/officer';

export const OFFICER_QUERY_KEYS = {
  officers: ['officers'] as const,
  officer: (id: number) => ['officers', id] as const,
  pendingReviews: ['officer', 'reviews', 'pending'] as const,
  districtFarmers: ['officer', 'farmers'] as const,
  districtFields: ['officer', 'fields'] as const,
  graphCandidates: (status: string) => ['officer', 'graph', 'candidates', status] as const,
  proactiveDecisions: ['officer', 'proactive', 'decisions'] as const,
  weatherAlerts: ['officer', 'weather', 'alerts'] as const,
};

/** Hook to fetch active officer profile. */
export function useOfficerProfile(officerId?: number) {
  return useQuery({
    queryKey: officerId ? OFFICER_QUERY_KEYS.officer(officerId) : OFFICER_QUERY_KEYS.officers,
    queryFn: async () => {
      if (officerId) {
        return await officerApi.getOfficer(officerId);
      }
      const list = await officerApi.listOfficers();
      return list.length > 0 ? list[0] : null;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Hook to query and manage pending Human-in-the-Loop advisory reviews. */
export function usePendingReviews() {
  const queryClient = useQueryClient();

  const reviewsQuery = useQuery({
    queryKey: OFFICER_QUERY_KEYS.pendingReviews,
    queryFn: () => reviewsApi.listPendingReviews(),
    staleTime: 15 * 1000,
    refetchInterval: 30 * 1000, // Poll every 30s
  });

  const reviewActionMutation = useMutation({
    mutationFn: ({
      alertId,
      payload,
    }: {
      alertId: number;
      payload: OfficerReviewActionRequest;
    }) => reviewsApi.takeAction(alertId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['officer', 'reviews'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  return {
    ...reviewsQuery,
    reviews: reviewsQuery.data ?? [],
    takeAction: reviewActionMutation.mutateAsync,
    isActionPending: reviewActionMutation.isPending,
  };
}

/** Hook to fetch registered farmers in jurisdiction. */
export function useDistrictFarmers() {
  const farmersQuery = useQuery({
    queryKey: OFFICER_QUERY_KEYS.districtFarmers,
    queryFn: () => farmerApi.listFarmers(),
    staleTime: 5 * 60 * 1000,
  });

  const fieldsQuery = useQuery({
    queryKey: OFFICER_QUERY_KEYS.districtFields,
    queryFn: () => farmerApi.listFields(),
    staleTime: 5 * 60 * 1000,
  });

  return {
    farmers: farmersQuery.data ?? [],
    fields: fieldsQuery.data ?? [],
    isLoading: farmersQuery.isLoading || fieldsQuery.isLoading,
    isError: farmersQuery.isError || fieldsQuery.isError,
  };
}

/** Hook to fetch and review Knowledge Graph candidates. */
export function useGraphCandidates(status: string = 'PENDING') {
  const queryClient = useQueryClient();

  const candidatesQuery = useQuery({
    queryKey: OFFICER_QUERY_KEYS.graphCandidates(status),
    queryFn: () => graphApi.listCandidates(status),
    staleTime: 60 * 1000,
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      candidateId,
      payload,
    }: {
      candidateId: number;
      payload: ReviewCandidateRequest;
    }) => graphApi.reviewCandidate(candidateId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['officer', 'graph'] });
    },
  });

  return {
    ...candidatesQuery,
    candidates: candidatesQuery.data ?? [],
    reviewCandidate: reviewMutation.mutateAsync,
    isReviewing: reviewMutation.isPending,
  };
}

/** Hook to fetch regional proactive risk decisions. */
export function useProactiveDecisions() {
  return useQuery({
    queryKey: OFFICER_QUERY_KEYS.proactiveDecisions,
    queryFn: () => alertsApi.listDecisions(),
    staleTime: 60 * 1000,
  });
}

/** Hook to fetch severe meteorological alerts. */
export function useSevereWeatherAlerts() {
  return useQuery({
    queryKey: OFFICER_QUERY_KEYS.weatherAlerts,
    queryFn: () => weatherApi.getAlerts(),
    staleTime: 60 * 1000,
  });
}

/** Hook to emit proactive regional agricultural events. */
export function useEmitEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: EventIngestRequest) => eventsApi.ingestEvent(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['officer', 'reviews'] });
      queryClient.invalidateQueries({ queryKey: ['officer', 'proactive'] });
    },
  });
}
