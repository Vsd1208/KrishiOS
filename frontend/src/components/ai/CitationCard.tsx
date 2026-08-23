import React from 'react';
import { BookOpen, Calendar, FileText, Award, Layers } from 'lucide-react';
import type { Citation } from '@/types/proactive';

export interface CitationCardProps {
  /** The citation object */
  citation: Citation;
  /** Optional citation reference number (e.g. 1, 2) */
  index?: number;
  /** Optional compact mode */
  compact?: boolean;
  /** Additional CSS class names */
  className?: string;
  /** Click handler if citation is interactive */
  onClick?: (citation: Citation) => void;
}

/**
 * Derives border accent style and badge styling based on relevance score (0-1 or 0-100).
 */
const getRelevanceDetails = (score?: number) => {
  if (score === undefined || score === null || isNaN(score)) {
    return {
      borderClass: 'border-l-border-strong',
      tagClass: 'bg-surface-raised text-text-muted border-border',
      label: 'Reference',
      normalized: undefined,
    };
  }

  const normalized = score > 1 ? score / 100 : Math.max(0, Math.min(1, score));
  const percent = Math.round(normalized * 100);

  if (normalized >= 0.8) {
    return {
      borderClass: 'border-l-success-500',
      tagClass: 'bg-success-50 text-success-700 border-success-200',
      label: `${percent}% match`,
      normalized,
    };
  }
  if (normalized >= 0.5) {
    return {
      borderClass: 'border-l-warning-500',
      tagClass: 'bg-warning-50 text-warning-700 border-warning-200',
      label: `${percent}% match`,
      normalized,
    };
  }
  return {
    borderClass: 'border-l-border-strong',
    tagClass: 'bg-surface-raised text-text-secondary border-border',
    label: `${percent}% match`,
    normalized,
  };
};

/**
 * CitationCard displays verifiable agricultural research, advisory, or statutory sources backing AI decisions.
 */
export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  index,
  compact = false,
  className = '',
  onClick,
}) => {
  const { source_title, authority, document_type, page, date, relevance_score, snippet } = citation;
  const relevance = getRelevanceDetails(relevance_score);

  const isInteractive = Boolean(onClick);

  return (
    <article
      tabIndex={isInteractive ? 0 : undefined}
      role={isInteractive ? 'button' : 'article'}
      onClick={() => onClick?.(citation)}
      onKeyDown={(e) => {
        if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.(citation);
        }
      }}
      className={`relative rounded-md border border-border bg-surface shadow-card transition-all border-l-4 ${
        relevance.borderClass
      } ${
        isInteractive
          ? 'cursor-pointer hover:shadow-raised hover:border-primary-300 focus-visible:ring-2 focus-visible:ring-primary-500'
          : ''
      } ${compact ? 'p-3 text-xs' : 'p-4 text-sm'} ${className}`}
      aria-label={`Citation: ${source_title}${authority ? `, by ${authority}` : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0 flex-1">
          {index !== undefined && (
            <span
              className={`inline-flex shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-800 font-semibold select-none ${
                compact ? 'w-4 h-4 text-[10px]' : 'w-5 h-5 text-xs'
              }`}
              aria-label={`Citation number ${index}`}
            >
              {index}
            </span>
          )}

          <div className="min-w-0 flex-1">
            <h4 className="font-semibold text-text leading-snug break-words">
              {source_title}
            </h4>

            {/* Metadata row: Authority, Doc Type, Date, Page */}
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary">
              {authority && (
                <span className="inline-flex items-center gap-1 font-medium text-text">
                  <Award className="w-3.5 h-3.5 text-primary-600 shrink-0" aria-hidden="true" />
                  <span className="truncate max-w-[200px]" title={authority}>
                    {authority}
                  </span>
                </span>
              )}

              {document_type && (
                <span className="inline-flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5 text-text-muted shrink-0" aria-hidden="true" />
                  <span>{document_type}</span>
                </span>
              )}

              {date && (
                <span className="inline-flex items-center gap-1 text-text-muted">
                  <Calendar className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>{date}</span>
                </span>
              )}

              {page !== undefined && page !== null && (
                <span className="inline-flex items-center gap-1 text-text-muted">
                  <BookOpen className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>p. {page}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Relevance badge */}
        {relevance.label && (
          <span
            className={`shrink-0 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none ${relevance.tagClass}`}
            title={`Relevance score: ${relevance.label}`}
          >
            <Layers className="w-3 h-3 shrink-0" aria-hidden="true" />
            <span>{relevance.label}</span>
          </span>
        )}
      </div>

      {/* Snippet quote */}
      {snippet && (
        <blockquote className="mt-2.5 rounded bg-surface-raised p-2.5 text-xs italic text-text-secondary border border-border/60 leading-relaxed font-sans">
          &ldquo;{snippet}&rdquo;
        </blockquote>
      )}
    </article>
  );
};

export default CitationCard;
