/**
 * ReviewModal Component.
 *
 * Side-by-side Human-in-the-Loop review modal.
 * Allows agricultural officers to inspect agent-synthesized advisories,
 * edit the advisory text before dispatch, add notes, and approve or reject.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { RiskBadge } from '@/components/ai/RiskBadge';
import {
  CheckCircle2,
  XCircle,
  Edit3,
  User,
  ShieldCheck,
} from 'lucide-react';
import type { AlertNotification, RiskSeverity } from '@/types/proactive';
import type { OfficerReviewActionRequest } from '@/types/officer';

interface ReviewModalProps {
  alert: AlertNotification | null;
  isOpen: boolean;
  onClose: () => void;
  onTakeAction: (alertId: number, payload: OfficerReviewActionRequest) => Promise<void>;
  isProcessing?: boolean;
}

export const ReviewModal: React.FC<ReviewModalProps> = ({
  alert,
  isOpen,
  onClose,
  onTakeAction,
  isProcessing,
}) => {
  const { t } = useTranslation();
  const [editedMessage, setEditedMessage] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (alert) {
      setEditedMessage(alert.message);
      setReviewNote('');
      setIsEditing(false);
      setFailed(false);
    }
  }, [alert]);

  if (!alert) return null;

  const severity: RiskSeverity =
    alert.priority === 'URGENT'
      ? 'CRITICAL'
      : alert.priority === 'HIGH'
        ? 'HIGH'
        : alert.priority === 'NORMAL'
          ? 'MEDIUM'
          : 'LOW';

  const submit = async (payload: OfficerReviewActionRequest) => {
    setFailed(false);
    try {
      await onTakeAction(alert.id, payload);
      onClose();
    } catch (err) {
      console.error('Review action failed:', err);
      setFailed(true); // keep the window open so the officer can try again
    }
  };

  const handleApprove = () =>
    submit({
      action: 'APPROVE',
      review_note: reviewNote.trim() || undefined,
      edited_message: isEditing && editedMessage.trim() !== alert.message ? editedMessage.trim() : undefined,
    });

  const handleReject = () =>
    submit({
      action: 'REJECT',
      review_note: reviewNote.trim() || 'Rejected during agronomist verification',
    });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('officer.review.title')}
      description={t('officer.review.description')}
      size="lg"
    >
      <div className="space-y-5">
        {/* Header Metadata */}
        <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg bg-surface-raised border border-border">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-primary-600" aria-hidden="true" />
            <span className="text-small font-bold text-text">{t('officer.farmerNo', { id: alert.farmer_id })}</span>
            <span className="text-caption text-text-muted">• {t('officer.review.channel', { channel: alert.channel })}</span>
          </div>
          <RiskBadge severity={severity} size="sm" />
        </div>

        {/* Advisory Title & Content */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-small font-bold text-text">{alert.title}</span>
            <button
              type="button"
              onClick={() => setIsEditing(!isEditing)}
              className="text-caption font-semibold text-primary-600 hover:text-primary-700 inline-flex items-center gap-1 cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{isEditing ? t('officer.review.cancelEdit') : t('officer.review.edit')}</span>
            </button>
          </div>

          {isEditing ? (
            <textarea
              value={editedMessage}
              onChange={(e) => setEditedMessage(e.target.value)}
              rows={5}
              className="w-full p-3 rounded-lg bg-surface border border-primary-400 text-small text-text focus:outline-none focus:ring-2 focus:ring-primary-500 font-sans"
              placeholder={t('officer.review.editPlaceholder')}
            />
          ) : (
            <div className="p-3.5 rounded-lg bg-surface border border-border text-small text-text whitespace-pre-line leading-relaxed">
              {editedMessage}
            </div>
          )}
        </div>

        {/* Officer Review Notes Input */}
        <div className="space-y-1.5">
          <label htmlFor="review-note" className="text-caption font-bold text-text uppercase block">
            {t('officer.review.note')}
          </label>
          <input
            id="review-note"
            type="text"
            value={reviewNote}
            onChange={(e) => setReviewNote(e.target.value)}
            placeholder={t('officer.review.notePlaceholder')}
            className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        {/* Officer Disclaimer */}
        <div className="p-3 rounded-lg bg-info-50 border border-info-200 text-info-900 text-caption flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p>
            {t('officer.review.disclaimer', { channel: alert.channel })}
          </p>
        </div>

        {failed && (
          <div role="alert" className="p-3 rounded-lg bg-danger-50 border border-danger-200 text-danger-800 text-small">
            {t('officer.review.failed')}
          </div>
        )}

        {/* Action Controls */}
        <div className="flex justify-between items-center pt-2 border-t border-border">
          <Button
            variant="danger"
            onClick={handleReject}
            disabled={isProcessing}
          >
            <XCircle className="w-4 h-4 mr-1.5" aria-hidden="true" />
            {t('officer.review.reject')}
          </Button>

          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} disabled={isProcessing}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleApprove}
              disabled={isProcessing}
            >
              <CheckCircle2 className="w-4 h-4 mr-1.5" aria-hidden="true" />
              {isProcessing ? t('officer.review.processing') : t('officer.review.approve')}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default ReviewModal;
