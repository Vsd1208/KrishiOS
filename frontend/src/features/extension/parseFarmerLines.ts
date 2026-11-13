import type { NewFarmer } from '@/services/api/extension';

/** One farmer per line: name, phone, language (te/hi/en), district id, village, acres. */
export function parseFarmerLines(
  text: string,
  consent: NewFarmer['consent'],
): { farmers: NewFarmer[]; errors: number[] } {
  const farmers: NewFarmer[] = [];
  const errors: number[] = [];
  text
    .split('\n')
    .map((l) => l.trim())
    .forEach((line, i) => {
      if (!line) return;
      const [full_name, phone, lang, district, village, acres] = line.split(',').map((c) => c.trim());
      const district_id = Number(district);
      const landholding_acres = Number(acres);
      if (
        !full_name ||
        !/^\+?\d{10,14}$/.test(phone ?? '') ||
        !['en', 'hi', 'te'].includes(lang ?? '') ||
        !Number.isInteger(district_id) ||
        !village ||
        !Number.isFinite(landholding_acres) ||
        landholding_acres < 0
      ) {
        errors.push(i + 1);
        return;
      }
      farmers.push({
        full_name,
        phone: phone as string,
        preferred_language: lang as NewFarmer['preferred_language'],
        district_id,
        village,
        landholding_acres,
        consent,
      });
    });
  return { farmers, errors };
}
