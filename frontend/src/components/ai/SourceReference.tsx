import React from 'react';
import { BookOpen } from 'lucide-react';

export interface SourceReferenceProps {
  /** Name/Title of the referenced source */
  source: string;
  /** Issuing organization/authority (e.g. "ICAR", "TNAU") */
  authority?: string;
  /** Relevance score (0 to 1) */
  relevance?: number;
  /** Optional index number for numbered citations (e.g. 1 -> [1]) */
  index?: number;
  /** Optional click handler when clicked/tapped */
  onClick?: () => void;
  /** Additional CSS class names */
  className?: string;
}

/**
 * Derives styling tokens based on relevance score.
 */
const getRelevanceStyle = (score?: number) => {
  if (score === undefined || score === null || isNaN(score)) {
    return {
      classes: 'bg-surface-raised border-border text-text-secondary hover:border-primary-300',
      dotClass: 'bg-text-muted',
    };
  }

  const normalized = score > 1 ? score / 100 : Math.max(0, Math.min(1, score));

  if (normalized >= 0.8) {
    return {
      classes:
        'bg-success-50/60 border-success-200 text-success-800 hover:bg-success-100 hover:border-success-300',
      dotClass: 'bg-success-500',
    };
  }
  if (normalized >= 0.5) {
    return {
      classes:
        'bg-warning-50/60 border-warning-200 text-warning-800 hover:bg-warning-100 hover:border-warning-300',
      dotClass: 'bg-warning-500',
    };
  }
  return {
    classes: 'bg-surface-raised border-border text-text-secondary hover:border-primary-300',
    dotClass: 'bg-text-muted',
  };
};

/**
 * Compact inline citation reference tag for embedding inside texts, tables, and AI explanations.
 */
export const SourceReference: React.FC<SourceReferenceProps> = ({
  source,
  authority,
  relevance,
  index,
  onClick,
  className = '',
}) => {
  const isClickable = Boolean(onClick);
  const relevanceStyle = getRelevanceStyle(relevance);
  const percentage =
    relevance !== undefined
      ? Math.round((relevance > 1 ? relevance / 100 : relevance) * 100)
      : null;

  const content = (
    <>
      <BookOpen className="w-3 h-3 shrink-0 opacity-70" aria-hidden="true" />

      {index !== undefined && (
        <span className="font-semibold select-none">[{index}]</span>
      )}

      <span className="truncate max-w-[220px] font-medium">{source}</span>

      {authority && (
        <span className="text-text-muted font-normal">({authority})</span>
      )}

      {percentage !== null && (
        <span className="inline-flex items-center gap-1 text-[10px] tabular-nums font-semibold opacity-85">
          <span className={`w-1.5 h-1.5 rounded-full ${relevanceStyle.dotClass}`} />
          {percentage}%
        </span>
      )}
    </>
  );

  const sharedClasses = `inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs transition-colors select-none ${
    relevanceStyle.classes
  } ${
    isClickable
      ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500'
      : ''
  } ${className}`;

  if (isClickable) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={sharedClasses}
        title={`Source: ${source}${authority ? ` (${authority})` : ''}${
          percentage ? ` - ${percentage}% relevance` : ''
        }`}
        aria-label={`Source citation: ${source}${authority ? ` by ${authority}` : ''}`}
      >
        {content}
      </button>
    );
  }

  return (
    <span
      className={sharedClasses}
      title={`Source: ${source}${authority ? ` (${authority})` : ''}${
        percentage ? ` - ${percentage}% relevance` : ''
      }`}
    >
      {content}
    </span>
  );
};

export default SourceReference;
