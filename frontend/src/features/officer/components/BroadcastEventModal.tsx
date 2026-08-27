/**
 * BroadcastEventModal Component.
 *
 * Allows agricultural officers to ingest an emergency agricultural event
 * (POST /api/v1/proactive/events) such as pest outbreak warnings, unseasonal
 * heavy rain alerts, or mandi price shifts.
 */

import React, { useState } from 'react';
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
  label: string;
  defaultCrop: string;
  defaultSeverity: string;
  defaultNotes: string;
}

const DEFAULT_EVENT_TEMPLATE: EventTemplate = {
  type: 'disease.outbreak.detected',
  label: 'Pest / Disease Outbreak Warning',
  defaultCrop: 'Paddy',
  defaultSeverity: 'HIGH',
  defaultNotes: 'Brown Plant Hopper (BPH) or Stem Borer threshold exceeded in region.',
};

const EVENT_TEMPLATES: EventTemplate[] = [
  DEFAULT_EVENT_TEMPLATE,
  {
    type: 'weather.alert.heavy_rainfall',
    label: 'Unseasonal Heavy Rainfall Warning',
    defaultCrop: 'Cotton',
    defaultSeverity: 'CRITICAL',
    defaultNotes: 'Forecast of 60mm+ rain in next 48h. Postpone spraying and harvest.',
  },
  {
    type: 'market.price.shift',
    label: 'Mandi Price Shock / Advisory',
    defaultCrop: 'Chilli',
    defaultSeverity: 'MEDIUM',
    defaultNotes: 'Significant upward shift in modal market prices.',
  },
];

export const BroadcastEventModal: React.FC<BroadcastEventModalProps> = ({
  isOpen,
  onClose,
  onEmitEvent,
}) => {
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState(0);
  const [crop, setCrop] = useState(DEFAULT_EVENT_TEMPLATE.defaultCrop);
  const [district, setDistrict] = useState('Khammam');
  const [notes, setNotes] = useState(DEFAULT_EVENT_TEMPLATE.defaultNotes);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<EventIngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTemplateChange = (idx: number) => {
    setSelectedTemplateIndex(idx);
    const tmpl = EVENT_TEMPLATES[idx] ?? DEFAULT_EVENT_TEMPLATE;
    setCrop(tmpl.defaultCrop);
    setNotes(tmpl.defaultNotes);
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
      setError(err instanceof Error ? err.message : 'Failed to ingest event into proactive pipeline.');
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
      title="Broadcast Regional Advisory Event"
      description="Trigger proactive risk intelligence across all registered farmers in district"
      size="lg"
    >
      {response ? (
        <div className="space-y-4 text-center py-4">
          <div className="w-14 h-14 rounded-full bg-success-50 text-success-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <h3 className="text-subheading font-bold text-text">Event Successfully Processed</h3>
            <p className="text-small text-text-secondary">{response.message}</p>
          </div>
          <div className="p-3 bg-surface-raised rounded-lg border border-border text-caption text-text-secondary text-left">
            <div>
              <strong>Decisions Generated:</strong> {response.decisions_count}
            </div>
            <div>
              <strong>Event ID:</strong> {response.event_id}
            </div>
          </div>
          <div className="flex justify-end pt-2">
            <Button variant="primary" onClick={handleReset}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Template Selector */}
          <div className="space-y-2">
            <label className="text-caption font-bold text-text uppercase block">
              Event Category:
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
                    <span>{tmpl.label}</span>
                  </div>
                  <span className="text-caption text-text-muted">{tmpl.defaultSeverity}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-caption font-bold text-text uppercase block mb-1">
                Target Crop:
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
                Target District:
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
              Advisory Instruction / Notes:
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
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              <Send className="w-4 h-4 mr-1.5" aria-hidden="true" />
              {isSubmitting ? 'Emitting...' : 'Broadcast Event'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};

export default BroadcastEventModal;
