/**
 * VoiceRecorderModal Component.
 *
 * Captures microphone audio using the browser MediaRecorder API,
 * submits the recording to the Multilingual Voice Intelligence endpoint
 * (POST /api/v1/voice/query), and displays the speech transcription,
 * detected language, agent decision, and spoken audio playback.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { CitationCard } from '@/components/ai/CitationCard';
import { ThinkingIndicator } from '@/components/ai/ThinkingIndicator';
import { voiceApi } from '@/services/api/voice';
import { Mic, Square, RefreshCw, AlertCircle, Sparkles } from 'lucide-react';
import type { VoiceQueryResponse } from '@/types/voice';

interface VoiceRecorderModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultLanguage?: 'te' | 'hi' | 'en';
}

export const VoiceRecorderModal: React.FC<VoiceRecorderModalProps> = ({
  isOpen,
  onClose,
  defaultLanguage = 'te',
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [languageHint, setLanguageHint] = useState<'te' | 'hi' | 'en'>(defaultLanguage);
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<VoiceQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isOpen) {
      // Clean up when modal closes
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
      setIsRecording(false);
      setRecordingSeconds(0);
      setIsProcessing(false);
      setResponse(null);
      setError(null);
    }
  }, [isOpen]);

  const startRecording = async () => {
    setError(null);
    setResponse(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm',
        });

        if (audioBlob.size === 0) {
          setError('No audio captured. Please speak into the microphone and try again.');
          return;
        }

        await processAudio(audioBlob);
      };

      mediaRecorder.start(200); // collect in 200ms slices
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone access denied:', err);
      setError('Microphone access denied or unavailable. Please enable microphone permissions in your browser.');
    }
  };

  const stopRecording = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (blob: Blob) => {
    setIsProcessing(true);
    setError(null);

    try {
      const res = await voiceApi.submitVoiceQuery(blob, 'farmer_voice.webm', {
        hintLanguage: languageHint,
      });
      setResponse(res);
    } catch (err) {
      console.error('Voice query failed:', err);
      setError(
        err instanceof Error ? err.message : 'Voice advisory processing failed. Please try again.',
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Voice Agricultural Advisory"
      description="Speak your question in Telugu, Hindi, or English"
      size="lg"
    >
      <div className="space-y-6">
        {/* Language Selector */}
        {!isRecording && !isProcessing && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-raised border border-border">
            <span className="text-small font-medium text-text">Spoken Language:</span>
            <div className="flex gap-1.5">
              {(
                [
                  { code: 'te', label: 'తెలుగు (Telugu)' },
                  { code: 'hi', label: 'हिंदी (Hindi)' },
                  { code: 'en', label: 'English' },
                ] as const
              ).map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLanguageHint(lang.code)}
                  className={`px-3 py-1 text-caption font-semibold rounded-md transition-colors cursor-pointer ${
                    languageHint === lang.code
                      ? 'bg-primary-600 text-white'
                      : 'bg-surface text-text-secondary hover:bg-gray-100'
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Recording Animation & Controls */}
        <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-surface-raised border border-border space-y-4">
          {isRecording ? (
            <>
              <div className="relative">
                <span className="absolute -inset-3 rounded-full bg-danger-400 opacity-75 animate-ping" />
                <button
                  type="button"
                  onClick={stopRecording}
                  className="relative w-20 h-20 rounded-full bg-danger-600 text-white flex items-center justify-center shadow-lg hover:bg-danger-700 active:scale-95 transition-all cursor-pointer"
                  aria-label="Stop recording"
                >
                  <Square className="w-8 h-8 fill-current" aria-hidden="true" />
                </button>
              </div>

              <div className="text-center space-y-1">
                <div className="text-heading font-bold text-danger-700">
                  {formatSeconds(recordingSeconds)}
                </div>
                <p className="text-caption text-text-secondary animate-pulse">
                  Listening... Tap square to submit
                </p>
              </div>
            </>
          ) : isProcessing ? (
            <div className="py-8 text-center space-y-3">
              <ThinkingIndicator message="Processing speech & synthesizing advisory..." />
            </div>
          ) : (
            <>
              <button
                type="button"
                onClick={startRecording}
                className="w-20 h-20 rounded-full bg-primary-600 text-white flex items-center justify-center shadow-lg hover:bg-primary-700 active:scale-95 transition-all cursor-pointer focus:outline-none focus-visible:ring-4 focus-visible:ring-primary-300"
                aria-label="Start recording"
              >
                <Mic className="w-9 h-9" aria-hidden="true" />
              </button>

              <div className="text-center space-y-0.5">
                <span className="text-body font-bold text-text block">
                  {response ? 'Ask Another Question' : 'Tap Microphone to Speak'}
                </span>
                <span className="text-caption text-text-secondary block">
                  e.g., &ldquo;వరిలో కాండం తొలుచు పురుగు నివారణ ఏమిటి?&rdquo;
                </span>
              </div>
            </>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3.5 rounded-lg bg-danger-50 border border-danger-200 text-danger-800 text-small flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-danger-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <p className="flex-1">{error}</p>
          </div>
        )}

        {/* Successful Advisory Response */}
        {response && (
          <div className="space-y-4 p-4 rounded-xl bg-surface border border-primary-200 shadow-sm animate-fadeIn">
            {/* Header & Meta */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary-600" aria-hidden="true" />
                <span className="text-small font-bold text-text">Voice Advisory Result</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-primary-50 text-primary-700">
                  {response.detected_language}
                </span>
              </div>
              <ConfidenceBadge confidence={response.confidence} showLabel />
            </div>

            {/* Farmer's Transcribed Question */}
            <div className="p-3 rounded-lg bg-surface-raised border border-border">
              <span className="text-[11px] uppercase font-bold text-text-muted block">
                Transcribed Query
              </span>
              <p className="text-body font-medium text-text mt-0.5">
                &ldquo;{response.raw_transcript}&rdquo;
              </p>
            </div>

            {/* AI Advisory Response Text */}
            <div className="space-y-2">
              <span className="text-[11px] uppercase font-bold text-primary-700 block">
                AI Agricultural Advisory
              </span>
              <p className="text-body text-text whitespace-pre-line leading-relaxed">
                {response.response_text}
              </p>
            </div>

            {/* Citations / Scientific Evidence */}
            {response.citations && response.citations.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border">
                <span className="text-caption font-semibold text-text-secondary">
                  Agricultural Sources &amp; Verification:
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {response.citations.map((c, idx) => (
                    <CitationCard
                      key={idx}
                      citation={{
                        source_title: c.source_title || 'ICAR / State Agricultural Advisory',
                        authority: c.authority || 'ICAR Research Institute',
                        document_type: c.document_type || 'Crop Advisory Guideline',
                        snippet: c.snippet,
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          {response && (
            <Button variant="primary" onClick={startRecording}>
              <RefreshCw className="w-4 h-4 mr-1.5" aria-hidden="true" />
              Ask Another
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default VoiceRecorderModal;
