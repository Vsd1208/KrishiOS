/**
 * UserMessageBubble Component.
 *
 * Displays the farmer's submitted question, attached crop photo,
 * voice transcript, and timestamp.
 */

import React from 'react';
import { Volume2, Image as ImageIcon } from 'lucide-react';
import type { UserMessageContent } from '@/features/ai/types/conversation';

interface UserMessageBubbleProps {
  content: UserMessageContent;
  timestamp: string;
}

export const UserMessageBubble: React.FC<UserMessageBubbleProps> = ({
  content,
  timestamp,
}) => {
  const { text, image, voice, language } = content;

  return (
    <div className="flex justify-end animate-fadeIn">
      <div className="max-w-2xl space-y-2 rounded-2xl rounded-tr-sm bg-primary-600 p-4 text-white shadow-md">
        {/* Attachments (Image or Voice Note) */}
        {image && (
          <div className="rounded-lg overflow-hidden border border-white/20 bg-black/20">
            <img
              src={image.previewUrl}
              alt="Farmer crop submission"
              className="max-h-52 w-full object-cover"
            />
            <div className="p-1.5 text-caption bg-black/40 text-white/90 flex items-center gap-1">
              <ImageIcon className="w-3 h-3" />
              <span>Attached Crop Photo ({image.cropHint || 'Paddy'})</span>
            </div>
          </div>
        )}

        {voice && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/10 text-caption font-semibold">
            <Volume2 className="w-4 h-4" />
            <span>Voice Query ({voice.durationSeconds}s) • {language?.toUpperCase() || 'TE'}</span>
          </div>
        )}

        {/* Text Content */}
        {text && (
          <p className="text-body font-normal leading-relaxed whitespace-pre-wrap">
            {text}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 text-[11px] text-white/70 pt-1 border-t border-white/10">
          <span>
            {language === 'te' ? 'Telugu' : language === 'hi' ? 'Hindi' : 'English'} Mode
          </span>
          <span>{timestamp}</span>
        </div>
      </div>
    </div>
  );
};

export default UserMessageBubble;
