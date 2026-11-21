import type { YieldForecast } from '@/services/api/forecasting';

const UNIT: Record<string, string> = {
  'Tonnes/Hectare': 't/ha',
  'bales_170kg/ha': 'bales/ha',
  'bales_180kg/ha': 'bales/ha',
  'nuts/ha': 'nuts/ha',
};

export const unitLabel = (u: string) => UNIT[u] ?? u;

export function cropName(f: Pick<YieldForecast, 'crop_names' | 'crop_canonical'>, lang: string): string {
  const names = f.crop_names as Record<string, string | undefined> | undefined;
  return names?.[lang] || names?.en || f.crop_canonical;
}

export type ReviewReason = 'tierB' | 'missing' | 'ood';

/** Why a forecast is less certain, in the order the officer should read them (Phase 10 findings). */
export function reviewReasons(
  f: Pick<YieldForecast, 'crop_tier' | 'missing_modalities' | 'in_distribution' | 'abstained'>,
): ReviewReason[] {
  if (f.abstained) return [];
  const out: ReviewReason[] = [];
  if (f.crop_tier === 'B') out.push('tierB');
  if (f.missing_modalities.length > 0) out.push('missing');
  if (!f.in_distribution) out.push('ood');
  return out;
}

/** "weather, past yields" in the reader's language; unknown inputs fall back to their code name. */
export function modalityList(names: string[], t: (key: string, opts?: Record<string, unknown>) => string): string {
  return names.map((m) => t(`yieldx.modality.${m}`, { defaultValue: m.replace(/_/g, ' ') })).join(', ');
}
