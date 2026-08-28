/**
 * AudioPlayerControls Component.
 *
 * Spoken advisory player featuring:
 * - Play / Pause / Replay toggle
 * - Speed rate switcher (0.75x, 1.0x, 1.25x)
 * - Multilingual audio synthesis (Telugu, Hindi, English)
 */

import React, { useState } from 'react';
import { Volume2, VolumeX, FastForward } from 'lucide-react';

interface AudioPlayerControlsProps {
  text: string;
  isPlaying: boolean;
  onTogglePlay: (rate: number) => void;
  language?: string;
}

export const AudioPlayerControls: React.FC<AudioPlayerControlsProps> = ({
  isPlaying,
  onTogglePlay,
}) => {
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);

  const rates = [0.75, 1.0, 1.25];

  const handleRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (isPlaying) {
      onTogglePlay(rate);
    }
  };

  return (
    <div className="inline-flex items-center gap-1.5 p-1 rounded-xl bg-surface border border-border text-caption shadow-xs">
      <button
        type="button"
        onClick={() => onTogglePlay(playbackRate)}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
          isPlaying
            ? 'bg-primary-600 text-white shadow-xs'
            : 'bg-primary-50 text-primary-800 hover:bg-primary-100'
        }`}
        aria-label={isPlaying ? 'Pause spoken advisory' : 'Listen to advisory in voice'}
      >
        {isPlaying ? (
          <>
            <VolumeX className="w-3.5 h-3.5" />
            <span>Stop</span>
          </>
        ) : (
          <>
            <Volume2 className="w-3.5 h-3.5" />
            <span>Listen Voice</span>
          </>
        )}
      </button>

      {/* Speed Rate Switcher */}
      <div className="flex items-center gap-0.5 border-l border-border pl-1.5">
        <FastForward className="w-3 h-3 text-text-muted mr-0.5" />
        {rates.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => handleRateChange(r)}
            className={`px-1.5 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-colors ${
              playbackRate === r
                ? 'bg-primary-100 text-primary-800'
                : 'text-text-muted hover:text-text'
            }`}
          >
            {r}x
          </button>
        ))}
      </div>
    </div>
  );
};

export default AudioPlayerControls;
