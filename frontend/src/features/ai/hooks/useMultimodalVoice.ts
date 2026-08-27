/**
 * Hook for capturing microphone audio and managing language hints.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { VoiceAttachment } from '@/features/ai/types/conversation';

export interface UseMultimodalVoiceReturn {
  isRecording: boolean;
  recordingSeconds: number;
  selectedLanguage: 'te' | 'hi' | 'en';
  setSelectedLanguage: (lang: 'te' | 'hi' | 'en') => void;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<VoiceAttachment | null>;
  cancelRecording: () => void;
  error: string | null;
}

export function useMultimodalVoice(
  initialLanguage: 'te' | 'hi' | 'en' = 'te'
): UseMultimodalVoiceReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState<'te' | 'hi' | 'en'>(initialLanguage);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const cleanupStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearTimer();
      cleanupStream();
    };
  }, [clearTimer, cleanupStream]);

  const startRecording = useCallback(async () => {
    setError(null);
    audioChunksRef.current = [];
    setRecordingSeconds(0);

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Microphone access is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
          ? 'audio/mp4'
          : 'audio/wav';

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(100);
      setIsRecording(true);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone error:', err);
      const msg =
        err instanceof Error ? err.message : 'Could not access microphone. Please check permissions.';
      setError(msg);
      setIsRecording(false);
      clearTimer();
      cleanupStream();
    }
  }, [clearTimer, cleanupStream]);

  const stopRecording = useCallback(async (): Promise<VoiceAttachment | null> => {
    clearTimer();
    const duration = recordingSeconds;

    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        setIsRecording(false);
        cleanupStream();
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        setIsRecording(false);
        cleanupStream();
        resolve({
          audioBlob,
          durationSeconds: Math.max(1, duration),
          detectedLanguage: selectedLanguage,
        });
      };

      recorder.stop();
    });
  }, [recordingSeconds, selectedLanguage, clearTimer, cleanupStream]);

  const cancelRecording = useCallback(() => {
    clearTimer();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setRecordingSeconds(0);
    audioChunksRef.current = [];
    cleanupStream();
  }, [clearTimer, cleanupStream]);

  return {
    isRecording,
    recordingSeconds,
    selectedLanguage,
    setSelectedLanguage,
    startRecording,
    stopRecording,
    cancelRecording,
    error,
  };
}
