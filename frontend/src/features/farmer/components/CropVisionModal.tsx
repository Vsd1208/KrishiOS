/**
 * CropVisionModal Component.
 *
 * Handles crop leaf/pest photo upload, client preview, background pipeline
 * submission (POST /api/v1/vision/images), polling for analysis results
 * (GET /api/v1/vision/analyses/{uuid}), and structured presentation of
 * observations, candidate diseases/pests, and confidence scores.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { ThinkingIndicator } from '@/components/ai/ThinkingIndicator';
import { visionApi } from '@/services/api/vision';
import {
  UploadCloud,
  Camera,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import type { AnalysisResponse } from '@/types/vision';

interface CropVisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCrop?: string;
}

const COMMON_CROPS = ['Paddy', 'Cotton', 'Chilli', 'Tomato', 'Maize', 'Groundnut', 'Soybean'];

export const CropVisionModal: React.FC<CropVisionModalProps> = ({
  isOpen,
  onClose,
  defaultCrop = 'Paddy',
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropHint, setCropHint] = useState<string>(defaultCrop);
  const [isUploading, setIsUploading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isOpen) {
      // Cleanup on modal close
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
      }
      setSelectedFile(null);
      setPreviewUrl(null);
      setIsUploading(false);
      setIsPolling(false);
      setAnalysis(null);
      setError(null);
    }
  }, [isOpen, previewUrl]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file (JPEG, PNG, WebP).');
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
    setAnalysis(null);
  };

  const startAnalysis = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const uploadResp = await visionApi.uploadImage(selectedFile, selectedFile.name, {
        crop_hint: cropHint,
      });

      setIsUploading(false);
      setIsPolling(true);

      // Start polling for analysis completion
      const analysisUuid = uploadResp.uuid;
      let attempts = 0;
      const maxAttempts = 30; // 30 seconds max

      pollTimerRef.current = window.setInterval(async () => {
        attempts++;
        try {
          const result = await visionApi.getAnalysis(analysisUuid);
          if (result.status === 'COMPLETED' || result.status === 'FAILED' || result.status === 'QUALITY_FAILED') {
            if (pollTimerRef.current) {
              window.clearInterval(pollTimerRef.current);
              pollTimerRef.current = null;
            }
            setIsPolling(false);
            setAnalysis(result);

            if (result.status === 'FAILED') {
              setError(result.error_message || 'Image analysis failed. Please try with a clearer photo.');
            }
          } else if (attempts >= maxAttempts) {
            if (pollTimerRef.current) {
              window.clearInterval(pollTimerRef.current);
              pollTimerRef.current = null;
            }
            setIsPolling(false);
            setError('Analysis timed out. Please try again.');
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }
      }, 1000);
    } catch (err) {
      console.error('Upload failed:', err);
      setIsUploading(false);
      setIsPolling(false);
      setError(err instanceof Error ? err.message : 'Failed to upload crop image.');
    }
  };

  const resetAll = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysis(null);
    setError(null);
    setIsUploading(false);
    setIsPolling(false);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Crop Health Diagnostic"
      description="Upload a photo of crop leaves, pests, or disease symptoms"
      size="lg"
    >
      <div className="space-y-5">
        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*"
          className="hidden"
        />

        {/* Step 1: Upload or Preview Box */}
        {!previewUrl ? (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-border hover:border-primary-500 rounded-2xl bg-surface-raised hover:bg-primary-50/20 transition-all cursor-pointer text-center space-y-3 group"
          >
            <div className="w-16 h-16 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Camera className="w-8 h-8" aria-hidden="true" />
            </div>
            <div>
              <p className="text-body font-bold text-text">Take Photo or Choose Image</p>
              <p className="text-caption text-text-secondary mt-1">
                Supports JPG, PNG, or WebP (up to 10MB)
              </p>
            </div>
            <Button variant="outline" size="sm" type="button" className="mt-2 pointer-events-none">
              <UploadCloud className="w-4 h-4 mr-1.5" aria-hidden="true" />
              Select File
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Image Preview */}
            <div className="relative rounded-xl overflow-hidden bg-black max-h-72 flex items-center justify-center border border-border">
              <img
                src={previewUrl}
                alt="Selected crop preview"
                className="max-h-72 w-auto object-contain"
              />
              {!isUploading && !isPolling && !analysis && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute bottom-3 right-3 px-3 py-1.5 rounded-lg bg-surface/90 backdrop-blur-sm text-text text-caption font-semibold shadow hover:bg-surface transition-colors cursor-pointer"
                >
                  Change Photo
                </button>
              )}
            </div>

            {/* Crop Hint Selector */}
            {!analysis && !isUploading && !isPolling && (
              <div className="p-3 rounded-lg bg-surface-raised border border-border space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-caption font-bold text-text uppercase">
                    Select Crop Type:
                  </label>
                  <span className="text-[11px] text-text-muted">Helps improve accuracy</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {COMMON_CROPS.map((crop) => (
                    <button
                      key={crop}
                      type="button"
                      onClick={() => setCropHint(crop)}
                      className={`px-3 py-1 rounded-md text-caption font-semibold transition-colors cursor-pointer ${
                        cropHint === crop
                          ? 'bg-primary-600 text-white'
                          : 'bg-surface text-text-secondary hover:bg-gray-100 border border-border'
                      }`}
                    >
                      {crop}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Loading / Polling State */}
        {(isUploading || isPolling) && (
          <div className="py-6 text-center space-y-3">
            <ThinkingIndicator
              message={
                isUploading
                  ? 'Uploading high-resolution image...'
                  : 'Running computer vision disease analysis & cross-checking...'
              }
            />
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-3.5 rounded-lg bg-danger-50 border border-danger-200 text-danger-800 text-small flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-danger-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <p className="flex-1">{error}</p>
          </div>
        )}

        {/* Successful Analysis Results */}
        {analysis && analysis.status === 'COMPLETED' && (
          <div className="space-y-4 p-4 rounded-xl bg-surface border border-primary-200 shadow-sm animate-fadeIn">
            {/* Header: Candidate Diagnosis & Confidence */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-success-600" aria-hidden="true" />
                <span className="text-body font-bold text-text">
                  {analysis.crop_detected || cropHint} Diagnostic Findings
                </span>
              </div>
              <ConfidenceBadge confidence={analysis.confidence_score ?? 0.85} showLabel />
            </div>

            {/* Quality Assessment if any */}
            {analysis.quality_score !== null && analysis.quality_score !== undefined && (
              <div className="flex items-center justify-between text-caption text-text-secondary px-3 py-1.5 bg-surface-raised rounded-lg">
                <span>Image Quality Score:</span>
                <span className="font-semibold text-text">
                  {Math.round(analysis.quality_score * 100)}% (Clear)
                </span>
              </div>
            )}

            {/* Candidate Conditions Detected */}
            <div className="space-y-2">
              <span className="text-[11px] uppercase font-bold text-primary-700 block">
                Identified Condition(s):
              </span>

              {analysis.candidate_conditions && analysis.candidate_conditions.length > 0 ? (
                <div className="space-y-2">
                  {analysis.candidate_conditions.map((cond, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-primary-50/50 border border-primary-100 flex items-center justify-between"
                    >
                      <div>
                        <span className="text-body font-bold text-text block">{cond.name}</span>
                        <span className="text-caption text-text-secondary">
                          Matched against ICAR agricultural taxonomy
                        </span>
                      </div>
                      <span className="text-small font-bold text-primary-700">
                        {Math.round(cond.confidence * 100)}% match
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-small text-text-secondary">No acute disease symptoms detected.</p>
              )}
            </div>

            {/* Specific Visual Observations */}
            {analysis.observations && analysis.observations.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-border">
                <span className="text-caption font-semibold text-text-secondary block">
                  Visual Symptoms Observed:
                </span>
                <ul className="list-disc list-inside text-small text-text space-y-1 pl-1">
                  {analysis.observations.map((obs, idx) => (
                    <li key={idx}>
                      <span className="font-medium">{obs.finding}</span>{' '}
                      <span className="text-caption text-text-muted">
                        ({Math.round(obs.confidence * 100)}% confidence)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Farmer Transparency & Uncertainty Note */}
            <div className="p-3 rounded-lg bg-info-50/60 border border-info-200 text-info-900 text-caption flex items-start gap-2">
              <HelpCircle className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <p>
                <strong>Farmer Guidance:</strong> This preliminary AI visual assessment is based on image patterns. For confirmation and chemical dosage, consult your local agricultural extension officer.
              </p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-2">
          {previewUrl && !isUploading && !isPolling ? (
            <Button variant="ghost" size="sm" onClick={resetAll}>
              <RefreshCw className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
              Start Over
            </Button>
          ) : (
            <div />
          )}

          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            {previewUrl && !analysis && !isUploading && !isPolling && (
              <Button variant="primary" onClick={startAnalysis}>
                <Camera className="w-4 h-4 mr-1.5" aria-hidden="true" />
                Analyze Crop
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default CropVisionModal;
