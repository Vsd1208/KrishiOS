/**
 * TypeScript types for Mandi Market Prices matching backend live_data schemas.
 *
 * See: backend/app/live_data/schemas/market.py
 */

export type MandiTrend = 'RISING' | 'FALLING' | 'STABLE' | 'UNKNOWN';

export interface MarketPriceObservation {
  commodity: string;
  variety: string;
  market: string;
  district: string;
  state: string;
  arrival_date: string;
  min_price_inr_quintal: number;
  max_price_inr_quintal: number;
  modal_price_inr_quintal: number;
  msp_inr_quintal?: number | null;
  price_trend: MandiTrend;
  arrivals_tonnes?: number | null;
  currency: string;
  unit: string;
  source_dataset?: string;
  fetched_at?: string;
  freshness_level?: 'FRESH' | 'RECENT' | 'STALE' | 'EXPIRED' | 'UNKNOWN';
}
