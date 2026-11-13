/** LGD district search (prefix) with optional block selection. */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { catalogApi, type District } from '@/services/api/govconnect';

export interface DistrictPickerProps {
  onPick: (district: District) => void;
  label?: string;
}

export const DistrictPicker: React.FC<DistrictPickerProps> = ({ onPick, label }) => {
  const { t } = useTranslation();
  const [q, setQ] = useState('');
  const { data = [] } = useQuery({
    queryKey: ['catalog', 'districts', q],
    queryFn: () => catalogApi.searchDistricts(q),
    enabled: q.trim().length >= 2,
  });
  return (
    <div className="relative">
      <label className="block text-caption text-text-secondary">
        {label ?? t('places.district')}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('places.searchDistrict')}
          className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
        />
      </label>
      {q.trim().length >= 2 && data.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full max-h-56 overflow-y-auto rounded-lg border border-border bg-surface shadow-card">
          {data.map((d) => (
            <li key={d.lgd_district_code}>
              <button
                type="button"
                onClick={() => {
                  onPick(d);
                  setQ('');
                }}
                className="w-full text-left px-3 py-1.5 text-small hover:bg-primary-50 cursor-pointer"
              >
                {d.district_name}, {d.state_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const BlockSelect: React.FC<{
  districtCode: number;
  value: number | null;
  onChange: (code: number | null) => void;
}> = ({ districtCode, value, onChange }) => {
  const { t } = useTranslation();
  const { data = [] } = useQuery({
    queryKey: ['catalog', 'blocks', districtCode],
    queryFn: () => catalogApi.blocks(districtCode),
  });
  return (
    <label className="block text-caption text-text-secondary">
      {t('places.block')}
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="block mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-small"
      >
        <option value="">{t('places.blockUnknown')}</option>
        {data.map((b) => (
          <option key={b.lgd_block_code} value={b.lgd_block_code}>
            {b.block_name}
          </option>
        ))}
      </select>
    </label>
  );
};
