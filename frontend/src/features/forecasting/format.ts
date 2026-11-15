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
