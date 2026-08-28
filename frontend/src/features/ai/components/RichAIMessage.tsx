/**
 * RichAIMessage Component.
 *
 * Adaptive AI decision intelligence message card featuring:
 * - Natural grounded agricultural answer
 * - Confidence metrics (ConfidenceBadge)
 * - Proactive risk communication (RiskBadge)
 * - Audio playback (AudioPlayerControls with speed options)
 * - Advisory action toolbar (Save, Print, Escalate)
 * - Expandable "Why this answer?" Evidence Drawer (ICAR Citations, Weather, Graph, Vision)
 * - Contextual follow-up suggestions
 */

import React, { useState } from 'react';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { RiskBadge } from '@/components/ai/RiskBadge';
import { CitationCard } from '@/components/ai/CitationCard';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';
import { AudioPlayerControls } from './AudioPlayerControls';
import { AdvisoryActionToolbar } from './AdvisoryActionToolbar';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  BookOpen,
  CloudRain,
  GitFork,
  Copy,
  Check,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import type { AIMessageContent } from '@/features/ai/types/conversation';

interface RichAIMessageProps {
  content: AIMessageContent;
  messageId: string;
  timestamp: string;
  isPlayingAudio?: boolean;
  onSpeak?: (text: string, lang: string, messageId: string, rate?: number) => void;
  onStopAudio?: () => void;
  onSelectFollowUp?: (prompt: string) => void;
  onEscalate?: () => void;
  crop?: string;
}

export const RichAIMessage: React.FC<RichAIMessageProps> = ({
  content,
  messageId,
  timestamp,
  isPlayingAudio = false,
  onSpeak,
  onStopAudio,
  onSelectFollowUp,
  onEscalate,
  crop = 'Paddy',
}) => {
  const [evidenceExpanded, setEvidenceExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const {
    text,
    confidence,
    citations = [],
    evidence,
    riskSeverity,
    liveContext,
    suggestedFollowUps = [],
  } = content;

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAudioToggle = (rate: number = 1.0) => {
    if (isPlayingAudio) {
      onStopAudio?.();
    } else {
      onSpeak?.(text, 'te-IN', messageId, rate);
    }
  };

  const hasEvidence = Boolean(
    citations.length > 0 ||
    evidence?.live_telemetry ||
    (evidence?.graph_paths && evidence.graph_paths.length > 0) ||
    (evidence?.vision_findings && evidence.vision_findings.length > 0)
  );

  return (
    <div className="space-y-3 max-w-3xl animate-fadeIn">
      {/* Main Advisory Bubble */}
      <div className="rounded-2xl border border-primary-200/90 bg-primary-50/30 p-4 sm:p-5 shadow-sm space-y-3.5 border-l-4 border-l-primary-600">
        {/* Header Metadata */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-primary-100/80 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-md bg-primary-100 px-2 py-0.5 text-caption font-bold text-primary-800">
              <Sparkles className="w-3.5 h-3.5 text-primary-700 shrink-0" aria-hidden="true" />
              KrishiOS Advisory
            </span>
            {riskSeverity && riskSeverity !== 'LOW' && (
              <RiskBadge severity={riskSeverity} size="sm" />
            )}
          </div>

          <div className="flex items-center gap-2">
            {confidence !== undefined && (
              <ConfidenceBadge confidence={confidence} size="sm" showLabel />
            )}
            <span className="text-caption text-text-muted">{timestamp}</span>
          </div>
        </div>

        {/* Advisory Body Text */}
        <div className="text-body leading-relaxed text-text font-normal whitespace-pre-line">
          {text}
        </div>

        {/* Live Weather / Spray Window Pill */}
        {liveContext && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-surface border border-border text-caption text-text-secondary flex-wrap">
            <CloudRain className="w-4 h-4 text-info-600 shrink-0" aria-hidden="true" />
            <span>
              Weather: <strong>{liveContext.temperatureCelsius}°C</strong> ({liveContext.weatherCondition})
            </span>
            <span>•</span>
            <span className={liveContext.sprayWindowFavorable ? 'text-success-700 font-bold' : 'text-danger-700 font-bold'}>
              Spray Window: {liveContext.sprayWindowFavorable ? 'Favorable' : 'Unfavorable'}
            </span>
          </div>
        )}

        {/* Uncertainty / Safety Notice for Moderate/Low Confidence */}
        {confidence !== undefined && confidence < 0.75 && (
          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-caption text-amber-900">
            <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <p>
              <strong>Field Verification Notice:</strong> This recommendation represents a possible risk identification based on available data, not a confirmed field diagnosis. Consult your local agricultural extension officer before heavy chemical application.
            </p>
          </div>
        )}

        {/* Action Controls Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-primary-100/70 text-caption">
          <div className="flex items-center gap-2">
            {/* Audio Speech Synthesis Button with Rate Switcher */}
            <AudioPlayerControls
              text={text}
              isPlaying={isPlayingAudio}
              onTogglePlay={handleAudioToggle}
            />

            {/* Copy Button */}
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface hover:bg-surface-raised text-text-secondary border border-border cursor-pointer transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-success-600" aria-hidden="true" />
                  <span className="text-success-700 font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          {/* Expandable "Why this answer?" Evidence Toggle */}
          {hasEvidence && (
            <button
              type="button"
              onClick={() => setEvidenceExpanded(!evidenceExpanded)}
              className="inline-flex items-center gap-1 font-bold text-primary-700 hover:text-primary-900 cursor-pointer"
            >
              <span>Why this answer? ({citations.length} sources)</span>
              {evidenceExpanded ? (
                <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
              )}
            </button>
          )}
        </div>

        {/* Action Toolbar (Save / Print / Escalate) */}
        <AdvisoryActionToolbar
          advisoryText={text}
          crop={crop}
          onEscalate={onEscalate}
        />

        {/* "Why this answer?" Evidence Drawer */}
        {evidenceExpanded && hasEvidence && (
          <div className="pt-3 space-y-3 border-t border-primary-200/80 animate-fadeIn text-small">
            {/* Citations Section */}
            {citations.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-caption font-bold text-text uppercase">
                  <span className="flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                    Verified ICAR &amp; Agronomic Literature
                  </span>
                  <FreshnessIndicator freshnessSeconds={3600} size="sm" />
                </div>
                <div className="space-y-2">
                  {citations.map((c, idx) => (
                    <CitationCard key={c.citation_id || idx} citation={c} index={idx + 1} compact />
                  ))}
                </div>
              </div>
            )}

            {/* Knowledge Graph Paths */}
            {evidence?.graph_paths && evidence.graph_paths.length > 0 && (
              <div className="space-y-1.5">
                <span className="flex items-center gap-1.5 text-caption font-bold text-text uppercase">
                  <GitFork className="w-3.5 h-3.5 text-purple-600" aria-hidden="true" />
                  Agronomic Knowledge Graph Context
                </span>
                {evidence.graph_paths.map((gp, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-surface border border-border text-caption font-mono text-text flex items-center justify-between"
                  >
                    <span>{gp.path}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-bold text-[10px]">
                      Verified Fact
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Contextual Follow-up Chips */}
      {suggestedFollowUps.length > 0 && (
        <div className="space-y-1.5 pl-1">
          <span className="text-caption font-bold text-text-muted uppercase block">
            Suggested Next Questions:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {suggestedFollowUps.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectFollowUp?.(prompt)}
                className="px-3 py-1.5 rounded-xl bg-surface border border-border text-caption text-text-secondary hover:text-primary-700 hover:border-primary-400 hover:bg-primary-50/50 transition-all cursor-pointer flex items-center gap-1 text-left shadow-xs"
              >
                <span>{prompt}</span>
                <ArrowRight className="w-3 h-3 text-text-muted shrink-0" aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RichAIMessage;
