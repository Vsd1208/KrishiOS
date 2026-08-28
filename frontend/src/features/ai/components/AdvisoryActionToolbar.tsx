/**
 * AdvisoryActionToolbar Component.
 *
 * Operational tools for farmer advisories:
 * - Save to Farm Notebook
 * - Export Printable Advisory Summary
 * - Escalate to Agronomist / Extension Officer
 */

import React, { useState } from 'react';
import { Bookmark, BookmarkCheck, Printer, Send, Check } from 'lucide-react';

interface AdvisoryActionToolbarProps {
  advisoryText: string;
  crop?: string;
  onEscalate?: () => void;
}

export const AdvisoryActionToolbar: React.FC<AdvisoryActionToolbarProps> = ({
  advisoryText,
  crop = 'Paddy',
  onEscalate,
}) => {
  const [saved, setSaved] = useState(false);
  const [escalated, setEscalated] = useState(false);

  const handleSave = () => {
    // Store in localStorage notebook
    try {
      const existing = JSON.parse(localStorage.getItem('krishios_notebook') || '[]');
      existing.unshift({
        id: `note-${Date.now()}`,
        crop,
        text: advisoryText,
        savedAt: new Date().toISOString(),
      });
      localStorage.setItem('krishios_notebook', JSON.stringify(existing));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.warn('Notebook storage error:', e);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleEscalate = () => {
    onEscalate?.();
    setEscalated(true);
    setTimeout(() => setEscalated(false), 4000);
  };

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border text-caption">
      {/* Save to Notebook */}
      <button
        type="button"
        onClick={handleSave}
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border transition-all cursor-pointer ${
          saved
            ? 'bg-success-50 text-success-800 border-success-300'
            : 'bg-surface hover:bg-surface-raised text-text-secondary border-border'
        }`}
        title="Save advisory to your personal farm notebook"
      >
        {saved ? (
          <>
            <BookmarkCheck className="w-3.5 h-3.5 text-success-600" />
            <span className="font-semibold text-success-700">Saved to Notebook</span>
          </>
        ) : (
          <>
            <Bookmark className="w-3.5 h-3.5" />
            <span>Save to Notebook</span>
          </>
        )}
      </button>

      {/* Print / Export */}
      <button
        type="button"
        onClick={handlePrint}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-raised text-text-secondary border border-border cursor-pointer transition-colors"
        title="Print or save as PDF"
      >
        <Printer className="w-3.5 h-3.5" />
        <span>Print Advisory</span>
      </button>

      {/* Escalate to Officer */}
      <button
        type="button"
        onClick={handleEscalate}
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border ml-auto transition-all cursor-pointer ${
          escalated
            ? 'bg-primary-50 text-primary-800 border-primary-300'
            : 'bg-primary-50 hover:bg-primary-100 text-primary-800 border-primary-200'
        }`}
        title="Submit this question directly to your Mandal Agricultural Officer"
      >
        {escalated ? (
          <>
            <Check className="w-3.5 h-3.5 text-primary-600" />
            <span className="font-semibold text-primary-700">Dispatched to Officer</span>
          </>
        ) : (
          <>
            <Send className="w-3.5 h-3.5 text-primary-600" />
            <span className="font-bold">Escalate to Officer</span>
          </>
        )}
      </button>
    </div>
  );
};

export default AdvisoryActionToolbar;
