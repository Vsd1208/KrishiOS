/** "My places" (F2): saved fields/villages with LGD district and block. Warnings and
 * advisories reach the farmer for every saved place, at block level when the source allows. */

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { MapPin, Star, Trash2 } from 'lucide-react';

import { locationsApi, type District } from '@/services/api/govconnect';
import { BlockSelect, DistrictPicker } from './DistrictPicker';

const KEY = ['farmer', 'locations'] as const;

export const LocationsCard: React.FC = () => {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: KEY, queryFn: locationsApi.list });
  const [label, setLabel] = useState('');
  const [district, setDistrict] = useState<District | null>(null);
  const [block, setBlock] = useState<number | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });
  const add = useMutation({
    mutationFn: () =>
      locationsApi.add({
        label,
        lgd_district_code: (district as District).lgd_district_code,
        lgd_block_code: block,
      }),
    onSuccess: () => {
      setLabel('');
      setDistrict(null);
      setBlock(null);
      void refresh();
    },
  });
  const remove = useMutation({ mutationFn: locationsApi.remove, onSuccess: refresh });
  const makePrimary = useMutation({
    mutationFn: (id: number) => {
      const loc = data.find((l) => l.id === id);
      if (!loc) throw new Error('missing');
      return locationsApi.update(id, { ...loc, is_primary: true });
    },
    onSuccess: refresh,
  });

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 space-y-3">
      <h2 className="text-body font-bold text-text flex items-center gap-2">
        <MapPin className="w-4 h-4 text-primary-600" aria-hidden="true" />
        {t('places.title')}
      </h2>
      <p className="text-caption text-text-muted">{t('places.help')}</p>
      <ul className="space-y-1.5">
        {data.map((l) => (
          <li key={l.id} className="flex items-center justify-between gap-2 rounded-lg bg-surface-raised px-3 py-2">
            <span className="text-small">
              <strong>{l.label}</strong> · {l.block_name ? `${l.block_name}, ` : ''}
              {l.district_name}, {l.state_name}
            </span>
            <span className="flex items-center gap-1">
              {l.is_primary ? (
                <span className="text-caption text-primary-700 font-semibold">{t('places.primary')}</span>
              ) : (
                <button
                  type="button"
                  aria-label={t('places.makePrimary')}
                  onClick={() => makePrimary.mutate(l.id)}
                  className="p-1 text-text-muted hover:text-primary-700 cursor-pointer"
                >
                  <Star className="w-4 h-4" aria-hidden="true" />
                </button>
              )}
              <button
                type="button"
                aria-label={t('places.remove')}
                onClick={() => remove.mutate(l.id)}
                className="p-1 text-text-muted hover:text-danger-700 cursor-pointer"
              >
                <Trash2 className="w-4 h-4" aria-hidden="true" />
              </button>
            </span>
          </li>
        ))}
      </ul>
      <form
        className="grid gap-2 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (district && label.trim()) add.mutate();
        }}
      >
        <label className="block text-caption text-text-secondary">
          {t('places.label')}
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder={t('places.labelHint')}
            className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
          />
        </label>
        {district ? (
          <div className="space-y-1">
            <p className="text-caption text-text-secondary">
              {district.district_name}, {district.state_name}{' '}
              <button
                type="button"
                onClick={() => setDistrict(null)}
                className="text-info-700 underline cursor-pointer"
              >
                {t('places.change')}
              </button>
            </p>
            <BlockSelect districtCode={district.lgd_district_code} value={block} onChange={setBlock} />
          </div>
        ) : (
          <DistrictPicker onPick={setDistrict} />
        )}
        <button
          type="submit"
          disabled={!district || !label.trim() || add.isPending}
          className="sm:col-span-2 justify-self-start px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer disabled:opacity-50"
        >
          {t('places.add')}
        </button>
        {add.isError && (
          <p role="alert" className="sm:col-span-2 text-caption text-danger-700">
            {t('chat.error')}
          </p>
        )}
      </form>
    </section>
  );
};
