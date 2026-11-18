/** Camera / gallery picker for photo questions (Phase 9). The photo goes only to KrishiOS's
 * local image model; it is downscaled in the browser first to keep uploads small. */

import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera } from 'lucide-react';

const MAX_SIDE = 1024;

async function downscale(file: File): Promise<Blob> {
  if (typeof createImageBitmap === 'undefined') return file;
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    if (scale === 1) return file;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext('2d')?.drawImage(bmp, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve) =>
      canvas.toBlob((b) => resolve(b ?? file), 'image/jpeg', 0.9),
    );
  } catch {
    return file;
  }
}

export const PhotoButton: React.FC<{ disabled?: boolean; onPicked: (photo: Blob) => void }> = ({
  disabled,
  onPicked,
}) => {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => input.current?.click()}
        aria-label={t('photo.add')}
        className="p-2 rounded-xl border border-border text-text cursor-pointer disabled:opacity-50"
      >
        <Camera className="w-4 h-4" aria-hidden="true" />
      </button>
      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        data-testid="photo-input"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          e.target.value = '';
          if (file) onPicked(await downscale(file));
        }}
      />
    </>
  );
};

export default PhotoButton;
