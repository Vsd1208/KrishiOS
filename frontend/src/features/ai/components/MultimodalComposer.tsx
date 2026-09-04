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

import React, {
  useState,
  useRef,
} from 'react';

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
  onSend: (
    content: UserMessageContent,
  ) => void;

  disabled?: boolean;

  farmContextLabel?: string;

  /**
   * Active crop supplied by the farmer workspace.
   *
   * This can be any crop; there is intentionally no
   * hardcoded Paddy/Cotton/Chilli list here.
   */
  crop?: string;
}

/* ============================================================
   COMPONENT
   ============================================================ */

export const MultimodalComposer: React.FC<
  MultimodalComposerProps
> = ({
  onSend,
  disabled = false,
  farmContextLabel =
    'Farm context unavailable',
  crop,
}) => {
  const [text, setText] =
    useState('');

  const [
    attachedImage,
    setAttachedImage,
  ] = useState<ImageAttachment | null>(
    null,
  );

  const [
    recordedVoice,
    setRecordedVoice,
  ] = useState<VoiceAttachment | null>(
    null,
  );

  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    );

  const textareaRef =
    useRef<HTMLTextAreaElement | null>(
      null,
    );

  /* ==========================================================
     VOICE
     ========================================================== */

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

  /* ==========================================================
     TEXT AUTO RESIZE
     ========================================================== */

  const resizeTextarea = () => {
    const textarea =
      textareaRef.current;

    if (!textarea) {
      return;
    }

    textarea.style.height =
      'auto';

    textarea.style.height = `${Math.min(
      textarea.scrollHeight,
      160,
    )}px`;
  };

  /* ==========================================================
     IMAGE SELECTION
     ========================================================== */

  const handleImageChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    /* --------------------------------------------------------
       Validate image format
       -------------------------------------------------------- */

    if (
      !file.type.startsWith(
        'image/',
      )
    ) {
      alert(
        'Please select a valid image file (JPG, PNG, WEBP).',
      );

      if (fileInputRef.current) {
        fileInputRef.current.value =
          '';
      }

      return;
    }

    /* --------------------------------------------------------
       Validate file size
       -------------------------------------------------------- */

    const maxSizeBytes =
      10 * 1024 * 1024;

    if (
      file.size >
      maxSizeBytes
    ) {
      alert(
        'Please select an image smaller than 10 MB.',
      );

      if (fileInputRef.current) {
        fileInputRef.current.value =
          '';
      }

      return;
    }

    /* --------------------------------------------------------
       Revoke previous preview
       -------------------------------------------------------- */

    if (
      attachedImage?.previewUrl
    ) {
      URL.revokeObjectURL(
        attachedImage.previewUrl,
      );
    }

    const previewUrl =
      URL.createObjectURL(file);

    setAttachedImage({
      file,
      previewUrl,

      /*
       * This is the important change:
       *
       * The image crop hint comes from the current farmer
       * crop context instead of being hardcoded to Paddy.
       */
      cropHint: crop,
    });

    if (fileInputRef.current) {
      fileInputRef.current.value =
        '';
    }
  };

  /* ==========================================================
     REMOVE IMAGE
     ========================================================== */

  const handleRemoveImage = () => {
    if (
      attachedImage?.previewUrl
    ) {
      URL.revokeObjectURL(
        attachedImage.previewUrl,
      );
    }

    setAttachedImage(null);
  };

  /* ==========================================================
     VOICE TOGGLE
     ========================================================== */

  const handleToggleRecord =
    async () => {
      if (isRecording) {
        const voice =
          await stopRecording();

        if (voice) {
          setRecordedVoice(
            voice,
          );
        }

        return;
      }

      setRecordedVoice(null);

      await startRecording();
    };

  /* ==========================================================
     REMOVE VOICE
     ========================================================== */

  const handleRemoveVoice = () => {
    setRecordedVoice(null);
  };

  /* ==========================================================
     SEND
     ========================================================== */

  const handleSend = () => {
    if (disabled) {
      return;
    }

    if (
      !text.trim() &&
      !attachedImage &&
      !recordedVoice
    ) {
      return;
    }

    onSend({
      text: text.trim(),

      image:
        attachedImage ||
        undefined,

      voice:
        recordedVoice ||
        undefined,

      language:
        selectedLanguage,
    });

    /* --------------------------------------------------------
       Reset composer state
       -------------------------------------------------------- */

    setText('');

    handleRemoveImage();

    setRecordedVoice(null);

    if (textareaRef.current) {
      textareaRef.current.style.height =
        'auto';
    }
  };

  /* ==========================================================
     KEYBOARD
     ========================================================== */

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey
    ) {
      event.preventDefault();

      handleSend();
    }
  };

  /* ==========================================================
     FORMAT RECORDING TIME
     ========================================================== */

  const formatRecordingTime =
    (seconds: number) => {
      const minutes =
        Math.floor(
          seconds / 60,
        );

      const remainingSeconds =
        seconds % 60;

      return `${String(
        minutes,
      ).padStart(
        2,
        '0',
      )}:${String(
        remainingSeconds,
      ).padStart(
        2,
        '0',
      )}`;
    };

  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <div className="w-full">
      {/* ======================================================
          CONTEXT
      ====================================================== */}

      <div className="mb-2 px-1 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="text-caption text-text-muted">
            Farm Context:{' '}
          </span>

          <strong className="text-caption text-text">
            {farmContextLabel}
          </strong>
        </div>

        {crop && (
          <span className="shrink-0 px-2 py-1 rounded-md bg-primary-50 text-primary-700 text-caption font-medium">
            {crop}
          </span>
        )}
      </div>

      {/* ======================================================
          VOICE ERROR
      ====================================================== */}

      {voiceError && (
        <div className="mb-2 flex items-start gap-2 rounded-lg border border-danger-200 bg-danger-50 px-3 py-2 text-caption text-danger-700">
          <AlertCircle
            className="w-3.5 h-3.5 shrink-0 mt-0.5"
            aria-hidden="true"
          />

          <span>
            {voiceError}
          </span>
        </div>
      )}

      {/* ======================================================
          ATTACHMENTS
      ====================================================== */}

      {(attachedImage ||
        recordedVoice) && (
        <div className="mb-2 flex flex-wrap gap-2">
          {/* ==================================================
              IMAGE PREVIEW
          ================================================== */}

          {attachedImage && (
            <div className="relative flex items-center gap-2 rounded-xl border border-border bg-surface-raised p-2">
              <img
                src={
                  attachedImage.previewUrl
                }
                alt="Selected crop"
                className="h-14 w-14 rounded-lg object-cover"
              />

              <div className="pr-5">
                <div className="flex items-center gap-1.5">
                  <FileImage
                    className="w-3.5 h-3.5 text-primary-600"
                    aria-hidden="true"
                  />

                  <span className="text-caption font-medium text-text">
                    Crop image
                  </span>
                </div>

                {crop && (
                  <span className="text-caption text-text-muted">
                    Context: {crop}
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={
                  handleRemoveImage
                }
                className="absolute right-1.5 top-1.5 rounded-md p-1 text-text-muted hover:bg-surface hover:text-danger-600"
                aria-label="Remove image"
              >
                <X
                  className="w-3.5 h-3.5"
                  aria-hidden="true"
                />
              </button>
            </div>
          )}

          {/* ==================================================
              VOICE PREVIEW
          ================================================== */}

          {recordedVoice && (
            <div className="relative flex items-center gap-2 rounded-xl border border-border bg-surface-raised px-3 py-2 pr-8">
              <Volume2
                className="w-4 h-4 text-primary-600"
                aria-hidden="true"
              />

              <div>
                <div className="text-caption font-medium text-text">
                  Voice query
                </div>

                <div className="text-caption text-text-muted">
                  Ready to send
                </div>
              </div>

              <button
                type="button"
                onClick={
                  handleRemoveVoice
                }
                className="absolute right-1.5 top-1.5 rounded-md p-1 text-text-muted hover:bg-surface hover:text-danger-600"
                aria-label="Remove voice recording"
              >
                <X
                  className="w-3.5 h-3.5"
                  aria-hidden="true"
                />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ======================================================
          MAIN COMPOSER
      ====================================================== */}

      <div className="rounded-2xl border border-border bg-surface shadow-xs focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
        {/* ====================================================
            TEXTAREA
        ==================================================== */}

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(event) => {
            setText(
              event.target.value,
            );

            resizeTextarea();
          }}
          onKeyDown={
            handleKeyDown
          }
          disabled={disabled}
          rows={1}
          placeholder={
            crop
              ? `Ask anything about ${crop}...`
              : 'Ask anything about your farm...'
          }
          className="w-full resize-none border-0 bg-transparent px-4 pt-3.5 pb-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-0 disabled:opacity-50"
          style={{
            maxHeight: '160px',
          }}
        />

        {/* ====================================================
            ACTION BAR
        ==================================================== */}

        <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5">
          <div className="flex items-center gap-1">
            {/* ==================================================
                IMAGE INPUT
            ================================================== */}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={
                handleImageChange
              }
              className="hidden"
              disabled={
                disabled
              }
            />

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() =>
                fileInputRef.current?.click()
              }
              disabled={
                disabled ||
                isRecording
              }
              title="Attach crop image"
              aria-label="Attach crop image"
            >
              <FileImage
                className="w-4 h-4"
                aria-hidden="true"
              />
            </Button>

            {/* ==================================================
                VOICE
            ================================================== */}

            <Button
              type="button"
              variant={
                isRecording
                  ? 'secondary'
                  : 'ghost'
              }
              size="sm"
              onClick={
                handleToggleRecord
              }
              disabled={
                disabled
              }
              title={
                isRecording
                  ? 'Stop recording'
                  : 'Record voice query'
              }
              aria-label={
                isRecording
                  ? 'Stop recording'
                  : 'Record voice query'
              }
            >
              {isRecording ? (
                <MicOff
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              ) : (
                <Mic
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              )}
            </Button>

            {/* ==================================================
                LANGUAGE
            ================================================== */}

            <select
              value={
                selectedLanguage
              }
              onChange={(event) =>
                setSelectedLanguage(
                  event.target.value as
                    | 'te'
                    | 'hi'
                    | 'en',
                )
              }
              disabled={
                disabled ||
                isRecording
              }
              className="h-8 rounded-lg border border-border bg-surface px-2 text-caption text-text focus:outline-none focus:ring-2 focus:ring-primary-100"
              aria-label="Voice language"
            >
              <option value="te">
                తెలుగు
              </option>

              <option value="hi">
                हिन्दी
              </option>

              <option value="en">
                English
              </option>
            </select>

            {/* ==================================================
                RECORDING TIMER
            ================================================== */}

            {isRecording && (
              <div className="flex items-center gap-1.5 px-2 text-caption text-danger-600">
                <span className="h-2 w-2 rounded-full bg-danger-500 animate-pulse" />

                <span>
                  {formatRecordingTime(
                    recordingSeconds,
                  )}
                </span>

                <button
                  type="button"
                  onClick={
                    () => {
                      cancelRecording();
                    }
                  }
                  className="ml-1 text-text-muted hover:text-danger-600"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {/* ====================================================
              SEND
          ==================================================== */}

          <Button
            type="button"
            size="sm"
            onClick={
              handleSend
            }
            disabled={
              disabled ||
              (
                !text.trim() &&
                !attachedImage &&
                !recordedVoice
              )
            }
            title="Send"
            aria-label="Send"
          >
            <Send
              className="w-4 h-4"
              aria-hidden="true"
            />

            <span className="hidden sm:inline ml-1.5">
              Send
            </span>
          </Button>
        </div>
      </div>

      {/* ======================================================
          HELP TEXT
      ====================================================== */}

      <div className="mt-1.5 px-1 flex items-center gap-1.5 text-caption text-text-muted">
        <Sparkles
          className="w-3 h-3 text-primary-500"
          aria-hidden="true"
        />

        <span>
          Press Enter to send · Shift+Enter
          for a new line
        </span>
      </div>
    </div>
  );
};

export default MultimodalComposer;