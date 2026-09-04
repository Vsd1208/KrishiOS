/**
 * MultimodalComposer Component.
 *
 * Full-featured input composer supporting:
 * - Multi-line auto-sizing text queries
 * - Voice audio capture with language hint selector
 * - Image attachment with instant preview thumbnail
 * - Mobile-first ergonomic touch layout
 *
 * Crop context is supplied by the parent page.
 * No crop is hardcoded here.
 */

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { useMultimodalVoice } from '@/features/ai/hooks/useMultimodalVoice';
import {
  Mic,
  MicOff,
  Send,
  X,
  Volume2,
  Sparkles,
  AlertCircle,
  FileImage,
} from 'lucide-react';
import type {
  UserMessageContent,
  ImageAttachment,
  VoiceAttachment,
} from '@/features/ai/types/conversation';

/* ============================================================
   PROPS
   ============================================================ */

interface MultimodalComposerProps {
  onSend: (content: UserMessageContent) => void;
  disabled?: boolean;
  farmContextLabel?: string;
  crop?: string;
}

/* ============================================================
   COMPONENT
   ============================================================ */

export const MultimodalComposer: React.FC<MultimodalComposerProps> = ({
  onSend,
  disabled = false,
  farmContextLabel = 'Farm context unavailable',
  crop,
}) => {
  const [text, setText] = useState('');
  const [attachedImage, setAttachedImage] = useState<ImageAttachment | null>(null);
  const [recordedVoice, setRecordedVoice] = useState<VoiceAttachment | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const {
    isRecording,
    recordingSeconds,
    selectedLanguage,
    setSelectedLanguage,
    startRecording,
    stopRecording,
    cancelRecording,
    error: voiceError,
  } = useMultimodalVoice('te');

  const resizeTextarea = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('Please select a valid image file (JPG, PNG, WEBP).');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const maxSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      alert('Please select an image smaller than 10 MB.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (attachedImage?.previewUrl) {
      URL.revokeObjectURL(attachedImage.previewUrl);
    }

    const previewUrl = URL.createObjectURL(file);
    setAttachedImage({
      file,
      previewUrl,
      cropHint: crop,
    });

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRemoveImage = () => {
    if (attachedImage?.previewUrl) {
      URL.revokeObjectURL(attachedImage.previewUrl);
    }
    setAttachedImage(null);
  };

  const handleToggleRecord = async () => {
    if (isRecording) {
      const voice = await stopRecording();
      if (voice) {
        setRecordedVoice(voice);
      }
      return;
    }

    setRecordedVoice(null);
    await startRecording();
  };

  const handleRemoveVoice = () => {
    setRecordedVoice(null);
  };

  const handleSend = () => {
    if (disabled) return;
    if (!text.trim() && !attachedImage && !recordedVoice) return;

    onSend({
      text: text.trim(),
      image: attachedImage || undefined,
      voice: recordedVoice || undefined,
      language: selectedLanguage,
    });

    setText('');
    handleRemoveImage();
    setRecordedVoice(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const canSend = Boolean(text.trim() || attachedImage || recordedVoice) && !disabled && !isRecording;

  return (
    <div className="border-t border-border/80 bg-surface/95 backdrop-blur-md p-3 sm:p-4 space-y-2.5 shadow-raised">
      {/* Context Badge */}
      <div className="flex items-center justify-between text-caption text-text-muted px-1">
        <div className="flex items-center gap-1.5 truncate">
          <Sparkles className="w-3.5 h-3.5 text-primary-600 shrink-0" aria-hidden="true" />
          <span className="truncate">
            Farm Context: <strong className="text-text font-semibold">{farmContextLabel}</strong>
          </span>
        </div>

        {/* Language Switcher */}
        <div className="flex items-center gap-1 shrink-0 bg-surface-raised/80 p-0.5 rounded-lg border border-border">
          <span className="text-[10px] font-bold text-text-muted px-1 uppercase">Lang:</span>
          {(['te', 'hi', 'en'] as const).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setSelectedLanguage(lang)}
              className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase transition-all cursor-pointer ${
                selectedLanguage === lang
                  ? 'bg-primary-600 text-white shadow-xs'
                  : 'text-text-secondary hover:text-text hover:bg-surface'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      {/* Attachments Tray */}
      {(attachedImage || recordedVoice || isRecording || voiceError) && (
        <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-surface-raised border border-border animate-fadeIn">
          {/* Image Thumbnail */}
          {attachedImage && (
            <div className="relative flex items-center gap-2.5 p-1.5 rounded-lg bg-surface border border-primary-300 shadow-xs">
              <img
                src={attachedImage.previewUrl}
                alt="Selected crop"
                className="h-12 w-12 rounded-lg object-cover"
              />
              <div className="text-caption pr-5">
                <span className="font-bold text-text block truncate max-w-[140px]">
                  {attachedImage.file.name}
                </span>
                <span className="text-primary-700 font-medium text-[11px]">
                  Crop Photo {crop ? `(${crop})` : ''}
                </span>
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="absolute top-1 right-1 p-1 rounded-full bg-danger-50 text-danger-700 hover:bg-danger-100 cursor-pointer transition-colors"
                aria-label="Remove image"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Recorded Audio Blob Chip */}
          {recordedVoice && !isRecording && (
            <div className="relative flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-50 border border-primary-300 text-caption text-primary-900 shadow-xs">
              <Volume2 className="w-4 h-4 text-primary-600" aria-hidden="true" />
              <span className="font-medium">Voice Note ({recordedVoice.durationSeconds}s)</span>
              <button
                type="button"
                onClick={handleRemoveVoice}
                className="p-1 rounded-full hover:bg-primary-200 cursor-pointer ml-1 transition-colors"
                aria-label="Remove audio"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Live Recording Overlay */}
          {isRecording && (
            <div className="flex items-center gap-3 flex-1 px-3.5 py-2 rounded-xl bg-danger-50 border border-danger-200 text-danger-900 animate-pulse">
              <span className="w-3 h-3 rounded-full bg-danger-600 animate-ping" />
              <span className="text-small font-bold">
                Listening ({selectedLanguage.toUpperCase()})... {recordingSeconds}s
              </span>
              <div className="ml-auto flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={cancelRecording}>
                  Cancel
                </Button>
                <Button variant="danger" size="sm" onClick={handleToggleRecord}>
                  Done
                </Button>
              </div>
            </div>
          )}

          {/* Voice Error Banner */}
          {voiceError && (
            <div className="flex items-center gap-1.5 text-caption text-danger-700 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{voiceError}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Input Row */}
      <div className="flex items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleImageChange}
          className="hidden"
          id="crop-image-upload"
        />

        <label
          htmlFor="crop-image-upload"
          className="p-2.5 rounded-xl border border-border bg-surface hover:bg-surface-raised text-text-secondary hover:text-primary-700 hover:border-primary-300 cursor-pointer transition-all shrink-0 flex items-center justify-center shadow-xs active:scale-95"
          title="Attach Crop Image"
        >
          <FileImage className="w-5 h-5 text-primary-600" aria-hidden="true" />
        </label>

        <button
          type="button"
          onClick={handleToggleRecord}
          className={`p-2.5 rounded-xl border transition-all shrink-0 flex items-center justify-center cursor-pointer shadow-xs active:scale-95 ${
            isRecording
              ? 'bg-danger-600 text-white border-danger-700 animate-bounce'
              : 'border-border bg-surface text-text-secondary hover:text-primary-700 hover:bg-surface-raised hover:border-primary-300'
          }`}
          title={isRecording ? 'Stop Recording' : 'Speak Question'}
          aria-label={isRecording ? 'Stop recording voice' : 'Record voice question'}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5 text-primary-600" />}
        </button>

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            resizeTextarea();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask in Telugu, Hindi, or English (e.g. నా వరి ఆకులు పసుపుగా మారుతున్నాయి)..."
          rows={1}
          disabled={disabled || isRecording}
          className="flex-1 p-2.5 max-h-32 min-h-[44px] rounded-xl bg-surface border border-border text-small text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 font-sans resize-none transition-all shadow-xs"
        />

        <Button
          variant="primary"
          onClick={handleSend}
          disabled={!canSend}
          className="h-[44px] px-5 rounded-xl shrink-0 cursor-pointer shadow-sm active:scale-95"
          aria-label="Send question"
        >
          <Send className="w-4 h-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
};

export default MultimodalComposer;
