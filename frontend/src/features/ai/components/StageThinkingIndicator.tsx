/**
 * StageThinkingIndicator Component.
 *
 * Displays multi-step reasoning progression (e.g. Vision -> RAG -> Synthesis)
 * matching actual backend execution stages without fabricating unperformed steps.
 */

import React from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import type { StageInfo } from '@/features/ai/types/conversation';

interface StageThinkingIndicatorProps {
  stageInfo: StageInfo;
}

export const StageThinkingIndicator: React.FC<StageThinkingIndicatorProps> = ({
  stageInfo,
}) => {
  const { message, detail, stepNumber, totalSteps } = stageInfo;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="p-4 rounded-2xl border border-primary-300 bg-primary-50/50 space-y-2 shadow-sm animate-fadeIn"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center text-primary-600">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            <Sparkles className="absolute w-2 h-2 text-primary-500 animate-ping opacity-75" aria-hidden="true" />
          </div>
          <span className="text-small font-bold text-text">{message}</span>
        </div>

        <span className="px-2 py-0.5 rounded-full text-caption font-semibold bg-primary-100 text-primary-800">
          Step {stepNumber} of {totalSteps}
        </span>
      </div>

      {detail && (
        <p className="text-caption text-text-secondary pl-6">
          {detail}
        </p>
      )}

      {/* Progress Bar */}
      <div className="h-1.5 w-full bg-primary-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-600 rounded-full transition-all duration-500"
          style={{ width: `${(stepNumber / totalSteps) * 100}%` }}
        />
      </div>
    </div>
  );
};

export default StageThinkingIndicator;
