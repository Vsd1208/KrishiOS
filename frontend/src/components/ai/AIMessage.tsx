import React, { useState } from 'react';
import { Sparkles, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import type { Citation } from '@/types/proactive';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { CitationCard } from '@/components/ai/CitationCard';

export interface AIMessageProps {
  /** The generated advisory or intelligence text */
  message: string;
  /** Optional confidence score (0-1) */
  confidence?: number;
  /** Optional supporting citations */
  citations?: Citation[];
  /** Optional custom CSS classes */
  className?: string;
  /** Optional timestamp or datetime label */
  timestamp?: string;
}

/**
 * Renders an AI-generated advisory message with confidence metrics, citations, and explainability indicators.
 */
export const AIMessage: React.FC<AIMessageProps> = ({
  message,
  confidence,
  citations,
  className = '',
  timestamp,
}) => {
  const [citationsExpanded, setCitationsExpanded] = useState(false);
  const hasCitations = citations && citations.length > 0;

  return (
    <article
      role="region"
      aria-label="AI Generated Advisory Message"
      className={`relative rounded-lg border border-primary-200/80 bg-primary-50/30 p-4.5 text-text shadow-sm border-l-4 border-l-primary-600 transition-all ${className}`}
    >
      {/* Header bar */}
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-primary-100/80 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-md bg-primary-100 px-2 py-0.5 text-xs font-semibold text-primary-800">
            <Sparkles className="w-3.5 h-3.5 text-primary-700 shrink-0" aria-hidden="true" />
            AI Advisory
          </span>

          {timestamp && (
            <span className="text-xs text-text-muted">{timestamp}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {confidence !== undefined && (
            <ConfidenceBadge confidence={confidence} size="sm" showLabel />
          )}
          <span className="text-[11px] uppercase tracking-wider text-text-muted font-medium select-none">
            KrishiOS Intelligence
          </span>
        </div>
      </header>

      {/* Message Content */}
      <div className="mt-3 text-sm leading-relaxed text-text font-normal whitespace-pre-wrap">
        {message}
      </div>

      {/* Citations Footer */}
      {hasCitations && (
        <footer className="mt-4 border-t border-primary-100/70 pt-3">
          <button
            type="button"
            onClick={() => setCitationsExpanded((prev) => !prev)}
            aria-expanded={citationsExpanded}
            aria-controls="ai-message-citations-list"
            className="flex items-center gap-1.5 text-xs font-medium text-primary-700 hover:text-primary-800 hover:underline focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-1 py-0.5 -ml-1"
          >
            <BookOpen className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span>
              {citations.length} Supporting Source{citations.length === 1 ? '' : 's'}
            </span>
            {citationsExpanded ? (
              <ChevronUp className="w-3.5 h-3.5 text-text-muted" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
            )}
          </button>

          {citationsExpanded && (
            <div
              id="ai-message-citations-list"
              className="mt-3 space-y-2 pt-1 animate-fade-in"
            >
              {citations.map((citation, idx) => (
                <CitationCard
                  key={citation.citation_id || `msg-cit-${idx}`}
                  citation={citation}
                  index={idx + 1}
                  compact
                />
              ))}
            </div>
          )}
        </footer>
      )}
    </article>
  );
};

export default AIMessage;
