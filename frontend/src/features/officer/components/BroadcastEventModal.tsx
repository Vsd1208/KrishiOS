/**
 * BroadcastEventModal Component.
 *
 * Allows agricultural officers to ingest an emergency agricultural event
 * (POST /api/v1/proactive/events) such as pest outbreak warnings, unseasonal
 * heavy rain alerts, or mandi price shifts.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Radio, Send, CheckCircle2 } from 'lucide-react';
import type { EventIngestRequest, EventIngestResponse } from '@/types/officer';

interface BroadcastEventModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEmitEvent: (payload: EventIngestRequest) => Promise<EventIngestResponse>;
}

interface EventTemplate {
  type: string;
  label: string; // i18n key
  defaultCrop: string;
  defaultSeverity: string;
  defaultNotes: string; // i18n key
}

const DEFAULT_EVENT_TEMPLATE: EventTemplate = {
  type: 'disease.outbreak.detected',
  label: 'officer.broadcast.tplPest',
  defaultCrop: 'Paddy',
  defaultSeverity: 'HIGH',
  defaultNotes: 'officer.broadcast.notesPest',
};

const EVENT_TEMPLATES: EventTemplate[] = [
  DEFAULT_EVENT_TEMPLATE,
  {
    type: 'weather.alert.heavy_rainfall',
    label: 'officer.broadcast.tplRain',
    defaultCrop: 'Cotton',
    defaultSeverity: 'CRITICAL',
    defaultNotes: 'officer.broadcast.notesRain',
  },
  {
    type: 'market.price.shift',
    label: 'officer.broadcast.tplPrice',
    defaultCrop: 'Chilli',
    defaultSeverity: 'MEDIUM',
    defaultNotes: 'officer.broadcast.notesPrice',
  },
];

export const BroadcastEventModal: React.FC<BroadcastEventModalProps> = ({
  isOpen,
  onClose,
  onEmitEvent,
}) => {
  const { t } = useTranslation();
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState(0);
  const [crop, setCrop] = useState(DEFAULT_EVENT_TEMPLATE.defaultCrop);
  const [district, setDistrict] = useState('Khammam');
  const [notes, setNotes] = useState(() => t(DEFAULT_EVENT_TEMPLATE.defaultNotes));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<EventIngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTemplateChange = (idx: number) => {
    setSelectedTemplateIndex(idx);
    const tmpl = EVENT_TEMPLATES[idx] ?? DEFAULT_EVENT_TEMPLATE;
    setCrop(tmpl.defaultCrop);
    setNotes(t(tmpl.defaultNotes));
    setResponse(null);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setResponse(null);

    const tmpl = EVENT_TEMPLATES[selectedTemplateIndex] ?? DEFAULT_EVENT_TEMPLATE;

    try {
      const res = await onEmitEvent({
        event_type: tmpl.type,
        source: 'officer_console',
        payload: {
          crop,
          district,
          state: 'Telangana',
          severity: tmpl.defaultSeverity,
          advisory_note: notes,
          broadcast_timestamp: new Date().toISOString(),
        },
      });
      setResponse(res);
    } catch (err) {
      console.error('Failed to emit event:', err);
      setError(t('officer.broadcast.failed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setResponse(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleReset}
      title={t('officer.broadcast.title')}
      description={t('officer.broadcast.description')}
      size="lg"
    >
      {response ? (
        <div className="space-y-4 text-center py-4">
          <div className="w-14 h-14 rounded-full bg-success-50 text-success-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <h3 className="text-subheading font-bold text-text">{t('officer.broadcast.sent')}</h3>
            <p className="text-small text-text-secondary">{response.message}</p>
          </div>
          <div className="p-3 bg-surface-raised rounded-lg border border-border text-caption text-text-secondary text-left">
            <div>
              <strong>{t('officer.broadcast.decisions')}</strong> {response.decisions_count}
            </div>
            <div>
              <strong>{t('officer.broadcast.eventId')}</strong> {response.event_id}
            </div>
          </div>
          <div className="flex justify-end pt-2">
            <Button variant="primary" onClick={handleReset}>
              {t('officer.broadcast.done')}
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Template Selector */}
          <div className="space-y-2">
            <label className="text-caption font-bold text-text uppercase block">
              {t('officer.broadcast.category')}
            </label>
            <div className="grid grid-cols-1 gap-2">
              {EVENT_TEMPLATES.map((tmpl, idx) => (
                <button
                  key={tmpl.type}
                  type="button"
                  onClick={() => handleTemplateChange(idx)}
                  className={`p-3 rounded-lg border text-small text-left transition-all cursor-pointer flex items-center justify-between ${
                    selectedTemplateIndex === idx
                      ? 'bg-primary-50 border-primary-500 text-primary-900 font-semibold shadow-sm'
                      : 'bg-surface border-border text-text hover:bg-surface-raised'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-primary-600" aria-hidden="true" />
                    <span>{t(tmpl.label)}</span>
                  </div>
                  <span className="text-caption text-text-muted">{t(`risk.${tmpl.defaultSeverity.toLowerCase()}`)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-caption font-bold text-text uppercase block mb-1">
                {t('officer.broadcast.crop')}
              </label>
              <input
                type="text"
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
                required
              />
            </div>

            <div>
              <label className="text-caption font-bold text-text uppercase block mb-1">
                {t('officer.broadcast.district')}
              </label>
              <input
                type="text"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
                required
              />
            </div>
          </div>

          {/* Advisory Notes */}
          <div>
            <label className="text-caption font-bold text-text uppercase block mb-1">
              {t('officer.broadcast.notes')}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full p-3 rounded-lg bg-surface border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
              required
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-danger-50 border border-danger-200 text-danger-800 text-small">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              {t('common.cancel')}
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              <Send className="w-4 h-4 mr-1.5" aria-hidden="true" />
              {isSubmitting ? t('officer.broadcast.sending') : t('officer.broadcast.submit')}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};

export default BroadcastEventModal;
