/**
 * Mandi Market Prices API Service.
 *
 * Interacts with:
 * - GET /api/v1/live/market/prices
 */

import { apiClient } from '@/services/api/client';
import type { MarketPriceObservation } from '@/types/market';

export interface MarketParams {
  commodity: string;
  state?: string;
  district?: string;
  force_refresh?: boolean;
}

export const marketApi = {
  /** Get mandi arrivals, modal prices, and MSP benchmarks. */
  async getMarketPrices(params: MarketParams): Promise<MarketPriceObservation[]> {
    const query = new URLSearchParams();
    query.set('commodity', params.commodity);
    if (params.state) query.set('state', params.state);
    if (params.district) query.set('district', params.district);
    if (params.force_refresh) query.set('force_refresh', 'true');

    return apiClient.get<MarketPriceObservation[]>(`/live/market/prices?${query.toString()}`);
  },
};
