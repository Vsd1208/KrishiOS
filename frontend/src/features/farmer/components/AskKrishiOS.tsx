/**
 * AskKrishiOS
 *
 * Compact AI assistant used in the farmer dashboard.
 *
 * Integrates:
 * - Text queries
 * - Voice modal
 * - Vision crop diagnosis modal
 * - Agent Runtime
 *
 * Crop context is supplied by the parent dashboard.
 * No crop is hardcoded here.
 */

import React, {
  useState,
} from 'react';

import {
  Image as ImageIcon,
  Loader2,
  Mic,
  Send,
  Sparkles,
  X,
} from 'lucide-react';

import { Button } from '@/components/ui/Button';

import { agentApi } from '@/services/api/agent';

import { VoiceRecorderModal } from '@/features/farmer/components/VoiceRecorderModal';

import { CropVisionModal } from '@/features/farmer/components/CropVisionModal';

import type {
  Farmer,
  FieldCrop,
} from '@/types/domain';

/* ============================================================
   QUICK QUESTIONS
   ============================================================ */

const SAMPLE_QUICK_QUESTIONS = [
  'What pests affect my crop?',
  'What is the recommended fertilizer dosage for my crop at the current stage?',
  'Is today favorable for spraying pesticide in my field?',
  'What are the current market rates for my crop?',
];

/* ============================================================
   TYPES
   ============================================================ */

interface AskKrishiOSProps {
  farmer?: Farmer | null;
  fieldCrops?: FieldCrop[];
  crop?: string;
}

/* ============================================================
   BACKEND HELPERS
   ============================================================ */

type CompactBackendResult = {
  agent?: string;
  output?: unknown;
};

type CompactBackendOutput = {
  recommendation?: string;
  answer?: string;
  hits?: Array<{
    chunk_text?: string;
    answer_context?: string;
  }>;
};

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    typeof value === 'object' &&
    value !== null
  );
}

function extractResultText(
  result: CompactBackendResult,
): string {
  const output =
    result.output;

  if (
    typeof output ===
    'string'
  ) {
    return output.trim();
  }

  if (
    !isRecord(output)
  ) {
    return '';
  }

  const typedOutput =
    output as CompactBackendOutput;

  if (
    typeof typedOutput.recommendation ===
      'string' &&
    typedOutput.recommendation.trim()
  ) {
    return typedOutput.recommendation.trim();
  }

  if (
    typeof typedOutput.answer ===
      'string' &&
    typedOutput.answer.trim()
  ) {
    return typedOutput.answer.trim();
  }

  if (
    Array.isArray(
      typedOutput.hits,
    )
  ) {
    return typedOutput.hits
      .map(
        (hit) =>
          hit.chunk_text ||
          hit.answer_context ||
          '',
      )
      .filter(Boolean)
      .join('\n\n');
  }

  return '';
}

/* ============================================================
   COMPONENT
   ============================================================ */

export const AskKrishiOS: React.FC<
  AskKrishiOSProps
> = ({
  farmer,
  fieldCrops: _fieldCrops,
  crop,
}) => {
  const [
    text,
    setText,
  ] = useState('');

  const [
    response,
    setResponse,
  ] = useState<string | null>(
    null,
  );

  const [
    isLoading,
    setIsLoading,
  ] = useState(false);

  const [
    showVoiceModal,
    setShowVoiceModal,
  ] = useState(false);

  const [
    showVisionModal,
    setShowVisionModal,
  ] = useState(false);

  /*
   * The parent supplies the active crop.
   *
   * No Paddy fallback is used.
   */
  const activeCropName =
    crop?.trim();

  const districtName =
    farmer?.village ||
    'Khammam';

  /* ==========================================================
     SEND QUERY
     ========================================================== */

  const sendQuery = async (
    query: string,
  ): Promise<void> => {
    const textToSend =
      query.trim();

    if (
      !textToSend ||
      isLoading
    ) {
      return;
    }

    setIsLoading(true);
    setResponse(null);

    try {
      const agentRequest = {
        goal: textToSend,

        state:
          'Telangana',

        district:
          districtName,

        season:
          'Kharif',

        ...(activeCropName
          ? {
              crop:
                activeCropName,
            }
          : {}),
      };

      console.info(
        '[KrishiOS] Compact assistant request:',
        agentRequest,
      );

      const result =
        await agentApi.execute(
          agentRequest,
        );

      const rawResults =
        isRecord(result) &&
        Array.isArray(
          result.results,
        )
          ? result.results
          : [];

      const typedResults = rawResults.filter((item) =>
  isRecord(item),
);

      /*
       * Prefer the crop advisory agent.
       */
      const advisoryResult =
        typedResults.find(
          (item) =>
            item.agent ===
            'crop_advisory_agent',
        );

      let finalText =
        advisoryResult
          ? extractResultText(
              advisoryResult,
            )
          : '';

      /*
       * If advisory output isn't available,
       * use verified retrieval output.
       */
      if (!finalText) {
        const retrievalResult =
          typedResults.find(
            (item) =>
              item.agent ===
              'knowledge_retrieval_agent',
          );

        if (retrievalResult) {
          finalText =
            extractResultText(
              retrievalResult,
            );
        }
      }

      /*
       * Safe direct-response fallback for compatible
       * API wrappers.
       */
      if (!finalText) {
        const directResult =
          result as unknown as {
            response?: unknown;
            answer?: unknown;
            recommendation?: unknown;
          };

        if (
          typeof directResult.response ===
          'string'
        ) {
          finalText =
            directResult.response;
        } else if (
          typeof directResult.answer ===
          'string'
        ) {
          finalText =
            directResult.answer;
        } else if (
          typeof directResult.recommendation ===
          'string'
        ) {
          finalText =
            directResult.recommendation;
        }
      }

      if (!finalText) {
        finalText =
          'I do not have enough verified information to answer that question right now.';
      }

      setResponse(
        finalText,
      );

      setText('');
    } catch (error) {
      console.error(
        'AskKrishiOS request failed:',
        error,
      );

      setResponse(
        'Unable to complete the agricultural analysis right now. Please try again.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  /* ==========================================================
     FORM
     ========================================================== */

  const handleSubmit = (
    event: React.FormEvent,
  ): void => {
    event.preventDefault();

    void sendQuery(text);
  };

  /* ==========================================================
     QUICK QUESTION
     ========================================================== */

  const handleQuickQuestion = (
    question: string,
  ): void => {
    void sendQuery(
      question,
    );
  };

  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <section className="rounded-2xl border border-border bg-surface shadow-xs overflow-hidden">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3">

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center">
            <Sparkles
              className="w-4 h-4"
              aria-hidden="true"
            />
          </div>

          <div>
            <h2 className="text-sm font-semibold text-text">
              Ask KrishiOS
            </h2>

            <p className="text-caption text-text-muted">
              {activeCropName
                ? `AI guidance for ${activeCropName}`
                : 'AI agricultural guidance'}
            </p>
          </div>
        </div>

        {activeCropName && (
          <span className="px-2.5 py-1 rounded-lg bg-primary-50 text-primary-700 text-caption font-medium">
            {activeCropName}
          </span>
        )}
      </div>

      {/* ======================================================
          RESPONSE
          ====================================================== */}

      {response && (
        <div className="px-4 py-3 border-b border-border bg-surface-raised">
          <div className="flex items-start justify-between gap-3">

            <div className="flex items-start gap-2 min-w-0">
              <Sparkles
                className="w-4 h-4 text-primary-600 shrink-0 mt-0.5"
                aria-hidden="true"
              />

              <p className="text-sm leading-6 text-text whitespace-pre-wrap">
                {response}
              </p>
            </div>

            <button
              type="button"
              onClick={() =>
                setResponse(null)
              }
              className="shrink-0 p-1 rounded-md text-text-muted hover:bg-surface hover:text-text"
              aria-label="Close response"
            >
              <X
                className="w-4 h-4"
                aria-hidden="true"
              />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================
          COMPOSER
          ====================================================== */}

      <form
        onSubmit={
          handleSubmit
        }
        className="p-3"
      >
        <div className="rounded-xl border border-border bg-surface focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">

          <textarea
            value={text}
            onChange={(event) =>
              setText(
                event.target.value,
              )
            }
            onKeyDown={(event) => {
              if (
                event.key ===
                  'Enter' &&
                !event.shiftKey
              ) {
                event.preventDefault();

                void sendQuery(
                  text,
                );
              }
            }}
            rows={3}
            disabled={
              isLoading
            }
            placeholder={
              activeCropName
                ? `Ask about ${activeCropName}...`
                : 'Ask about your crop...'
            }
            className="w-full resize-none border-0 bg-transparent px-3 py-3 text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-0"
          />

          <div className="px-2 pb-2 flex items-center justify-between gap-2">

            <div className="flex items-center gap-1">

              {/* VOICE */}

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  setShowVoiceModal(
                    true,
                  )
                }
                disabled={
                  isLoading
                }
                title="Ask using voice"
                aria-label="Ask using voice"
              >
                <Mic
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              </Button>

              {/* VISION */}

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  setShowVisionModal(
                    true,
                  )
                }
                disabled={
                  isLoading
                }
                title="Diagnose crop image"
                aria-label="Diagnose crop image"
              >
                <ImageIcon
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              </Button>
            </div>

            {/* SEND */}

            <Button
              type="submit"
              size="sm"
              disabled={
                isLoading ||
                !text.trim()
              }
            >
              {isLoading ? (
                <Loader2
                  className="w-4 h-4 animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <Send
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              )}

              <span className="ml-1.5">
                {isLoading
                  ? 'Thinking...'
                  : 'Ask'}
              </span>
            </Button>
          </div>
        </div>

        {/* ====================================================
            QUICK QUESTIONS
            ==================================================== */}

        <div className="mt-3">

          <div className="flex items-center gap-1.5 mb-2">
            <Sparkles
              className="w-3.5 h-3.5 text-primary-600"
              aria-hidden="true"
            />

            <span className="text-caption font-medium text-text-muted">
              Quick questions
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUICK_QUESTIONS.map(
              (question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() =>
                    handleQuickQuestion(
                      question,
                    )
                  }
                  disabled={
                    isLoading
                  }
                  className="px-2.5 py-1.5 rounded-lg border border-border bg-surface-raised text-caption text-text-secondary hover:border-primary-300 hover:bg-primary-50/40 hover:text-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {question}
                </button>
              ),
            )}
          </div>
        </div>
      </form>

      {/* ======================================================
          VOICE MODAL
          ====================================================== */}

      <VoiceRecorderModal
        isOpen={
          showVoiceModal
        }
        onClose={() =>
          setShowVoiceModal(
            false,
          )
        }
        defaultLanguage="te"
      />

      {/* ======================================================
          VISION MODAL
          ====================================================== */}

      <CropVisionModal
        isOpen={
          showVisionModal
        }
        onClose={() =>
          setShowVisionModal(
            false,
          )
        }
        defaultCrop={
          activeCropName
        }
      />
    </section>
  );
};

export default AskKrishiOS;