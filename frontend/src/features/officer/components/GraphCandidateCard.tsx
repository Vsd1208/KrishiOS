/**
 * GraphCandidateCard Component.
 *
 * Renders an agronomic knowledge graph candidate extracted by GraphRAG
 * with subject -> predicate -> object relationships, confidence score,
 * and 1-click Approve / Reject actions.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { Check, X, ArrowRight } from 'lucide-react';
import type { GraphCandidate, ReviewCandidateRequest } from '@/types/officer';

interface GraphCandidateCardProps {
  candidate: GraphCandidate;
  onReview: (candidateId: number, payload: ReviewCandidateRequest) => Promise<void>;
  isProcessing?: boolean;
}

export const GraphCandidateCard: React.FC<GraphCandidateCardProps> = ({
  candidate,
  onReview,
  isProcessing,
}) => {
  const { t } = useTranslation();
  const [note, setNote] = useState('');
  const isPending = candidate.review_status === 'PENDING';
  const isApproved = candidate.review_status === 'APPROVED';

  return (
    <Card
      variant="default"
      padding="md"
      className={`border-l-4 transition-all ${
        isApproved
          ? 'border-l-success-500 bg-surface'
          : isPending
            ? 'border-l-purple-500 bg-purple-50/20'
            : 'border-l-gray-300 bg-surface opacity-75'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-2 flex-1">
          {/* Relationship Triple Header */}
          <div className="flex items-center gap-2 flex-wrap text-small">
            <span className="px-2.5 py-1 rounded-md bg-purple-100 text-purple-900 font-bold">
              {candidate.subject_name}
            </span>
            <span className="text-caption font-semibold text-text-muted flex items-center gap-1 uppercase">
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              {candidate.predicate}
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
            <span className="px-2.5 py-1 rounded-md bg-primary-100 text-primary-900 font-bold">
              {candidate.object_name}
            </span>
            <ConfidenceBadge confidence={candidate.confidence} size="sm" showLabel />
          </div>

          {/* Node Labels and Provenance */}
          <div className="flex items-center gap-x-3 gap-y-1 flex-wrap text-caption text-text-secondary">
            <span>{t('officer.cand.subject')} <strong className="text-text">{candidate.subject_label}</strong></span>
            <span>•</span>
            <span>{t('officer.cand.object')} <strong className="text-text">{candidate.object_label}</strong></span>
            <span>•</span>
            <span>{t('officer.cand.doc')} <code className="text-[11px] text-text-muted">{candidate.document_uuid.slice(0, 8)}...</code></span>
          </div>

          {/* Optional Note input */}
          {isPending && (
            <div className="pt-1">
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t('officer.cand.notePlaceholder')}
                className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-shrink-0 self-end sm:self-center">
          {isPending ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReview(candidate.id, { action: 'REJECT', note })}
                disabled={isProcessing}
                className="text-danger-600 hover:bg-danger-50 border-danger-200"
              >
                <X className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
                {t('officer.cand.reject')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onReview(candidate.id, { action: 'APPROVE', note })}
                disabled={isProcessing}
              >
                <Check className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
                {t('officer.cand.approve')}
              </Button>
            </>
          ) : (
            <span
              className={`px-3 py-1 rounded-full text-caption font-semibold ${
                isApproved
                  ? 'bg-success-50 text-success-700 border border-success-200'
                  : 'bg-gray-100 text-gray-700 border border-gray-200'
              }`}
            >
              {t(`officer.status.${candidate.review_status}`)}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
};

export default GraphCandidateCard;
