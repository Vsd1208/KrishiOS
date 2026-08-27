/**
 * MultimodalComposer Component.
 *
 * Full-featured input composer supporting:
 * - Multi-line auto-sizing text queries
 * - Voice audio capture with language hint selector ('te', 'hi', 'en')
 * - Image attachment with instant preview thumbnail
 * - Mobile-first ergonomic touch layout
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

interface MultimodalComposerProps {
  onSend: (content: UserMessageContent) => void;
  disabled?: boolean;
  farmContextLabel?: string;
}

export const MultimodalComposer: React.FC<MultimodalComposerProps> = ({
  onSend,
  disabled = false,
  farmContextLabel = 'Paddy • 4.5 Ac (Khammam)',
}) => {
  const [text, setText] = useState('');
  const [attachedImage, setAttachedImage] = useState<ImageAttachment | null>(null);
  const [recordedVoice, setRecordedVoice] = useState<VoiceAttachment | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  // Handle Image Selection
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate image format
    if (!file.type.startsWith('image/')) {
      alert('Please select a valid image file (JPG, PNG, WEBP).');
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    setAttachedImage({
      file,
      previewUrl,
      cropHint: 'Paddy',
    });

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRemoveImage = () => {
    if (attachedImage?.previewUrl) {
      URL.revokeObjectURL(attachedImage.previewUrl);
    }
    setAttachedImage(null);
  };

  // Handle Voice Stop & Store
  const handleToggleRecord = async () => {
    if (isRecording) {
      const voice = await stopRecording();
      if (voice) {
        setRecordedVoice(voice);
      }
    } else {
      setRecordedVoice(null);
      await startRecording();
    }
  };

  const handleRemoveVoice = () => {
    setRecordedVoice(null);
  };

  // Submit Content
  const handleSend = () => {
    if ((!text.trim() && !attachedImage && !recordedVoice) || disabled) return;

    onSend({
      text: text.trim(),
      image: attachedImage || undefined,
      voice: recordedVoice || undefined,
      language: selectedLanguage,
    });

    // Reset composer state
    setText('');
    handleRemoveImage();
    setRecordedVoice(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = Boolean(text.trim() || attachedImage || recordedVoice) && !disabled && !isRecording;

  return (
    <div className="border-t border-border bg-surface p-3 sm:p-4 space-y-2 shadow-lg">
      {/* Context Badge */}
      <div className="flex items-center justify-between text-caption text-text-muted px-1">
        <div className="flex items-center gap-1.5 truncate">
          <Sparkles className="w-3.5 h-3.5 text-primary-600 shrink-0" aria-hidden="true" />
          <span className="truncate">
            Farm Context: <strong className="text-text">{farmContextLabel}</strong>
          </span>
        </div>

        {/* Language Switcher */}
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[11px] font-semibold text-text-muted">Lang:</span>
          {(['te', 'hi', 'en'] as const).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setSelectedLanguage(lang)}
              className={`px-1.5 py-0.5 rounded text-[11px] font-bold uppercase transition-colors cursor-pointer ${
                selectedLanguage === lang
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-raised text-text-secondary hover:text-text'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      {/* Attachments Tray (Image preview or Voice recording badge) */}
      {(attachedImage || recordedVoice || isRecording || voiceError) && (
        <div className="flex flex-wrap items-center gap-2 p-2 rounded-xl bg-surface-raised border border-border animate-fadeIn">
          {/* Image Thumbnail */}
          {attachedImage && (
            <div className="relative flex items-center gap-2 p-1.5 rounded-lg bg-surface border border-primary-300">
              <img
                src={attachedImage.previewUrl}
                alt="Attached crop"
                className="w-12 h-12 object-cover rounded-md"
              />
              <div className="text-caption pr-4">
                <span className="font-bold text-text block truncate max-w-[120px]">
                  {attachedImage.file.name}
                </span>
                <span className="text-text-muted text-[11px]">Crop Image Attached</span>
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="absolute top-1 right-1 p-0.5 rounded-full bg-danger-100 text-danger-700 hover:bg-danger-200 cursor-pointer"
                aria-label="Remove image"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Recorded Audio Blob Chip */}
          {recordedVoice && !isRecording && (
            <div className="relative flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-50 border border-primary-300 text-caption text-primary-900">
              <Volume2 className="w-4 h-4 text-primary-600" aria-hidden="true" />
              <span>Voice Note ({recordedVoice.durationSeconds}s)</span>
              <button
                type="button"
                onClick={handleRemoveVoice}
                className="p-0.5 rounded-full hover:bg-primary-200 cursor-pointer ml-1"
                aria-label="Remove audio"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Live Recording Overlay */}
          {isRecording && (
            <div className="flex items-center gap-3 flex-1 px-3 py-2 rounded-lg bg-danger-50 border border-danger-200 text-danger-900 animate-pulse">
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
            <div className="flex items-center gap-1.5 text-caption text-danger-700">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{voiceError}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Input Row */}
      <div className="flex items-end gap-2">
        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleImageChange}
          className="hidden"
          id="crop-image-upload"
        />

        {/* Action Button: Attach Image */}
        <label
          htmlFor="crop-image-upload"
          className="p-2.5 rounded-xl border border-border bg-surface-raised text-text-secondary hover:text-text hover:bg-surface cursor-pointer transition-colors shrink-0 flex items-center justify-center"
          title="Attach Crop Image"
        >
          <FileImage className="w-5 h-5 text-primary-600" aria-hidden="true" />
        </label>

        {/* Action Button: Toggle Microphone */}
        <button
          type="button"
          onClick={handleToggleRecord}
          className={`p-2.5 rounded-xl border transition-all shrink-0 flex items-center justify-center cursor-pointer ${
            isRecording
              ? 'bg-danger-600 text-white border-danger-700 animate-bounce'
              : 'border-border bg-surface-raised text-text-secondary hover:text-text hover:bg-surface'
          }`}
          title={isRecording ? 'Stop Recording' : 'Speak Question'}
          aria-label={isRecording ? 'Stop recording voice' : 'Record voice question'}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5 text-primary-600" />}
        </button>

        {/* Textarea Input */}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask in Telugu, Hindi, or English (e.g. నా వరి ఆకులు పసుపుగా మారుతున్నాయి)..."
          rows={1}
          disabled={disabled || isRecording}
          className="flex-1 p-2.5 max-h-32 min-h-[44px] rounded-xl bg-surface-raised border border-border text-small text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500 font-sans resize-none"
        />

        {/* Send Action */}
        <Button
          variant="primary"
          onClick={handleSend}
          disabled={!canSend}
          className="h-[44px] px-4 rounded-xl shrink-0 cursor-pointer shadow-sm"
          aria-label="Send question"
        >
          <Send className="w-4 h-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
};

export default MultimodalComposer;
