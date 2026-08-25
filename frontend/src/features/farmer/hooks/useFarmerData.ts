/**
 * Custom React Query hooks for Farmer domain data.
 *
 * Integrates:
 * - Farmer profile & active fields
 * - Live weather & forecast
 * - Mandi commodity market prices
 * - Proactive risk alerts & acknowledgments
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { farmerApi } from '@/services/api/farmer';
import { weatherApi } from '@/services/api/weather';
import { marketApi } from '@/services/api/market';
import { alertsApi } from '@/services/api/alerts';
import { advisoryApi } from '@/services/api/advisory';
import type { AlertStatus } from '@/types/proactive';

export const FARMER_QUERY_KEYS = {
  farmers: ['farmers'] as const,
  farmer: (id: number) => ['farmers', id] as const,
  fields: ['fields'] as const,
  field: (id: number) => ['fields', id] as const,
  crops: ['crops'] as const,
  fieldCrops: ['field-crops'] as const,
  soilSamples: ['soil-samples'] as const,
  currentWeather: (district?: string, fieldId?: number) =>
    ['weather', 'current', district, fieldId] as const,
  forecast: (district?: string, fieldId?: number, days?: number) =>
    ['weather', 'forecast', district, fieldId, days] as const,
  weatherAlerts: ['weather', 'alerts'] as const,
  marketPrices: (commodity: string, district?: string) =>
    ['market', 'prices', commodity, district] as const,
  alerts: (farmerId?: number, status?: AlertStatus) =>
    ['alerts', farmerId, status] as const,
  advisories: (crop: string, district?: string) =>
    ['advisories', crop, district] as const,
  preferences: (farmerId?: number) => ['preferences', farmerId] as const,
};

/** Hook to fetch all farmers and return the active farmer profile. */
export function useFarmerProfile(farmerId?: number) {
  return useQuery({
    queryKey: farmerId ? FARMER_QUERY_KEYS.farmer(farmerId) : FARMER_QUERY_KEYS.farmers,
    queryFn: async () => {
      if (farmerId) {
        return await farmerApi.getFarmerById(farmerId);
      }
      const list = await farmerApi.listFarmers();
      return list.length > 0 ? list[0] : null;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/** Hook to fetch registered fields for a farmer. */
export function useFarmerFields(farmerId?: number) {
  return useQuery({
    queryKey: FARMER_QUERY_KEYS.fields,
    queryFn: async () => {
      const allFields = await farmerApi.listFields();
      if (farmerId) {
        return allFields.filter((f) => f.farmer_id === farmerId);
      }
      return allFields;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** Hook to fetch standing crops & field crops. */
export function useFarmerCrops() {
  const cropsQuery = useQuery({
    queryKey: FARMER_QUERY_KEYS.crops,
    queryFn: () => farmerApi.listCrops(),
    staleTime: 10 * 60 * 1000,
  });

  const fieldCropsQuery = useQuery({
    queryKey: FARMER_QUERY_KEYS.fieldCrops,
    queryFn: () => farmerApi.listFieldCrops(),
    staleTime: 5 * 60 * 1000,
  });

  return {
    crops: cropsQuery.data ?? [],
    fieldCrops: fieldCropsQuery.data ?? [],
    isLoading: cropsQuery.isLoading || fieldCropsQuery.isLoading,
    isError: cropsQuery.isError || fieldCropsQuery.isError,
    error: cropsQuery.error || fieldCropsQuery.error,
  };
}

/** Hook to fetch live weather observations. */
export function useCurrentWeather(district?: string, fieldId?: number) {
  return useQuery({
    queryKey: FARMER_QUERY_KEYS.currentWeather(district, fieldId),
    queryFn: () => weatherApi.getCurrentWeather({ district, field_id: fieldId }),
    staleTime: 15 * 60 * 1000, // 15 minutes
    refetchInterval: 15 * 60 * 1000,
  });
}

/** Hook to fetch 7-day weather forecast with spray window advisory. */
export function useWeatherForecast(district?: string, fieldId?: number, days: number = 7) {
  return useQuery({
    queryKey: FARMER_QUERY_KEYS.forecast(district, fieldId, days),
    queryFn: () => weatherApi.getForecast({ district, field_id: fieldId, days }),
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

/** Hook to fetch Mandi market prices for farmer's crop. */
export function useMarketPrices(commodity: string, district?: string) {
  return useQuery({
    queryKey: FARMER_QUERY_KEYS.marketPrices(commodity, district),
    queryFn: () => marketApi.getMarketPrices({ commodity, district }),
    enabled: Boolean(commodity),
    staleTime: 30 * 60 * 1000,
  });
}

/** Hook to fetch active proactive alerts and acknowledge them. */
export function useFarmerAlerts(farmerId?: number, statusFilter?: AlertStatus) {
  const queryClient = useQueryClient();

  const alertsQuery = useQuery({
    queryKey: FARMER_QUERY_KEYS.alerts(farmerId, statusFilter),
    queryFn: () => alertsApi.listAlerts({ farmer_id: farmerId, status_filter: statusFilter }),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Poll every minute for new proactive alerts
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: number) => alertsApi.acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  return {
    ...alertsQuery,
    alerts: alertsQuery.data ?? [],
    acknowledgeAlert: acknowledgeMutation.mutate,
    isAcknowledging: acknowledgeMutation.isPending,
  };
}

/** Hook to fetch ICAR and State agromet advisories. */
export function useCropAdvisories(crop: string, district?: string) {
  return useQuery({
    queryKey: FARMER_QUERY_KEYS.advisories(crop, district),
    queryFn: () => advisoryApi.getAdvisories({ crop, district }),
    enabled: Boolean(crop),
    staleTime: 30 * 60 * 1000,
  });
}
