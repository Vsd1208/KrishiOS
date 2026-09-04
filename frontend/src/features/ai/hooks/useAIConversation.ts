/**
 * Central AI Decision Intelligence Conversation Engine Hook.
 *
 * Responsibilities:
 * - Text, voice, and vision input handling
 * - Agent Runtime execution
 * - Dynamic farmer crop context
 * - Grounded evidence and citation assembly
 * - Backend validation handling
 * - Weather context
 * - Multi-stage processing indicators
 * - Browser TTS playback
 *
 * Crop handling is intentionally crop-agnostic.
 * No crop whitelist or Paddy fallback is used here.
 */

import { useCallback, useRef, useState } from 'react';

import { agentApi } from '@/services/api/agent';
import { visionApi } from '@/services/api/vision';
import { weatherApi } from '@/services/api/weather';

import type {
  ChatMessage,
  UserMessageContent,
  StageInfo,
  ProcessingStage,
} from '@/features/ai/types/conversation';

import type {
  Citation,
  EvidencePackage,
} from '@/types/proactive';

/* ============================================================
   BACKEND TYPES
   ============================================================ */

type BackendCitation = {
  citation_id?: string;
  title?: string;
  source_title?: string;
  source?: string | null;
  source_url?: string | null;
  authority?: string;
  document_type?: string;
  page_number?: string | number | null;
  page?: string | number | null;
  snippet?: string;
  confidence?: number;
  relevance_score?: number;
};

type RetrievalHit = {
  chunk_text?: string;
  answer_context?: string;
  score?: number;
  ranking_score?: number;
  freshness_score?: number;
  authority_score?: number;
  citation?: BackendCitation;
};

type BackendAgentOutput = {
  recommendation?: string;
  answer?: string;
  hits?: RetrievalHit[];
  context_used?: boolean;
  passed?: boolean;
  validated_text?: string;
  [key: string]: unknown;
};

type BackendAgentResult = {
  agent: string;
  status?: string;
  output?: BackendAgentOutput | string;
  confidence?: number;
  grounded?: boolean;
  citations?: BackendCitation[];
  error?: string | null;
};

/* ============================================================
   SUGGESTIONS
   ============================================================ */

const INITIAL_SUGGESTIONS = [
  'What pests affect my crop?',
  'What is the recommended fertilizer schedule for my crop?',
  'My crop leaves are turning yellow, what could be the reason?',
  "Will tomorrow's weather be favorable for pesticide spraying?",
];

function getInitialSuggestions(crop?: string): string[] {
  const cropName = crop?.trim();

  if (!cropName) {
    return INITIAL_SUGGESTIONS;
  }

  return [
    `What pests affect ${cropName}?`,
    `What is the recommended fertilizer schedule for ${cropName}?`,
    `My ${cropName} crop leaves are turning yellow, what could be the reason?`,
    "Will tomorrow's weather be favorable for pesticide spraying?",
  ];
}

/* ============================================================
   CROP CONTEXT RESOLUTION
   ============================================================ */

/**
 * Resolve a crop explicitly mentioned by the farmer.
 *
 * This intentionally does not use a fixed crop dictionary.
 * Any crop name can be returned.
 */
function resolveCropForQuery(
  query: string,
  defaultCrop?: string,
): string | undefined {
  const normalizedDefault = defaultCrop?.trim();
  if (normalizedDefault) {
    return normalizedDefault;
  }

  const normalizedQuery = query
    .toLowerCase()
    .replace(/[?!.,;:()[\]{}]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  /*
   * "What pests affect chilli?"
   * "What diseases affect maize?"
   * "Problems affecting cotton"
   */
  const affectPattern =
    /\b(?:affect|affecting|infect|infecting)\s+([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,3})\b/i;

  const affectMatch = normalizedQuery.match(affectPattern);

  if (affectMatch?.[1]) {
    const candidate = cleanCropCandidate(affectMatch[1]);

    if (candidate) {
      return candidate;
    }
  }

  /*
   * "fertilizer schedule for paddy"
   * "pests of chilli"
   * "diseases of maize"
   * "management for cotton"
   */
  const relationPattern =
    /\b(?:pests?|diseases?|problems?|management|cultivation|farming|yield|production|fertilizer|schedule|dosage|irrigation|spray|treatment)\s+(?:of|for|in|on)\s+(?:my\s+)?([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,3})\b/i;

  const relationMatch = normalizedQuery.match(relationPattern);

  if (relationMatch?.[1]) {
    const candidate = cleanCropCandidate(relationMatch[1]);

    if (candidate) {
      return candidate;
    }
  }

  /*
   * "fertilizer for maize crop"
   * "pests in cotton crop"
   */
  const cropSuffixPattern =
    /\b(?:for|in|on|of)\s+(?:my\s+)?([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,3})\s+crop\b/i;

  const cropSuffixMatch = normalizedQuery.match(cropSuffixPattern);

  if (cropSuffixMatch?.[1]) {
    const candidate = cleanCropCandidate(cropSuffixMatch[1]);

    if (candidate) {
      return candidate;
    }
  }

  /*
   * "maize crop"
   * "cotton crop"
   * "red gram crop"
   */
  const explicitCropPattern =
    /\b([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,3})\s+crop\b/i;

  const explicitCropMatch = normalizedQuery.match(explicitCropPattern);

  if (explicitCropMatch?.[1]) {
    const candidate = cleanCropCandidate(explicitCropMatch[1]);

    if (candidate) {
      return candidate;
    }
  }

  /*
   * "for paddy" at the end of inquiry
   */
  const tailPattern =
    /\b(?:for|in|on|of)\s+(?:my\s+)?([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,2})$/i;

  const tailMatch = normalizedQuery.match(tailPattern);

  if (tailMatch?.[1]) {
    const candidate = cleanCropCandidate(tailMatch[1]);

    if (candidate) {
      return candidate;
    }
  }

  return undefined;
}

function cleanCropCandidate(candidate: string): string | undefined {
  const ignoredWords = new Set([
    'a',
    'an',
    'the',
    'is',
    'are',
    'was',
    'were',
    'am',
    'be',
    'been',
    'being',
    'do',
    'does',
    'did',
    'have',
    'has',
    'had',
    'can',
    'could',
    'shall',
    'should',
    'will',
    'would',
    'may',
    'might',
    'must',
    'my',
    'your',
    'our',
    'this',
    'that',
    'these',
    'those',
    'for',
    'in',
    'on',
    'at',
    'to',
    'from',
    'by',
    'with',
    'about',
    'crop',
    'crops',
    'field',
    'fields',
    'farm',
    'farmer',
    'plant',
    'plants',
    'pest',
    'pests',
    'disease',
    'diseases',
    'problem',
    'problems',
    'management',
    'cultivation',
    'farming',
    'production',
    'yield',
    'fertilizer',
    'schedule',
    'dosage',
    'irrigation',
    'harvesting',
    'spray',
    'treatment',
    'today',
    'current',
    'best',
    'recommended',
    'what',
    'which',
    'how',
    'why',
    'when',
    'where',
    'tell',
    'me',
  ]);

  const words = candidate
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  while (words.length > 0) {
    const firstWord = words[0];

    if (!firstWord || !ignoredWords.has(firstWord.toLowerCase())) {
      break;
    }

    words.shift();
  }

  while (words.length > 0) {
    const lastIndex = words.length - 1;
    const lastWord = words[lastIndex];

    if (!lastWord || !ignoredWords.has(lastWord.toLowerCase())) {
      break;
    }

    words.pop();
  }

  const cleaned = words.join(' ').trim();

  return cleaned || undefined;
}

/* ============================================================
   TYPE GUARDS
   ============================================================ */

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isBackendCitation(value: unknown): value is BackendCitation {
  return isRecord(value);
}

function isRetrievalHit(value: unknown): value is RetrievalHit {
  return isRecord(value);
}

function isBackendAgentResult(
  value: unknown,
): value is BackendAgentResult {
  if (!isRecord(value)) {
    return false;
  }

  return typeof value.agent === 'string';
}

function isBackendAgentOutput(
  value: unknown,
): value is BackendAgentOutput {
  return isRecord(value);
}

/* ============================================================
   CONTEXT
   ============================================================ */

export interface AIConversationContext {
  crop?: string;
  state?: string;
  district?: string;
  season?: string;
}

/* ============================================================
   HOOK
   ============================================================ */

export function useAIConversation(
  context: AIConversationContext = {},
) {
  const {
    crop,
    state = 'Telangana',
    district = 'Khammam',
    season = 'Kharif',
  } = context;

  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [activeStage, setActiveStage] =
    useState<StageInfo | null>(null);

  const [isProcessing, setIsProcessing] =
    useState(false);

  const [isPlayingAudio, setIsPlayingAudio] =
    useState(false);

  const [
    currentPlayingMessageId,
    setCurrentPlayingMessageId,
  ] = useState<string | null>(null);

  const sessionIdRef = useRef<string>(
    `session-${Date.now()}`,
  );

  /* ==========================================================
     PROCESSING STAGE
     ========================================================== */

  const setStage = useCallback(
    (
      stage: ProcessingStage,
      message: string,
      stepNumber: number,
      totalSteps: number,
      detail?: string,
    ) => {
      setActiveStage({
        stage,
        message,
        stepNumber,
        totalSteps,
        detail,
      });
    },
    [],
  );

  /* ==========================================================
     TEXT TO SPEECH
     ========================================================== */

  const speakText = useCallback(
    (
      text: string,
      lang: string = 'te-IN',
      messageId?: string,
      rate: number = 1.0,
    ) => {
      if (!('speechSynthesis' in window)) {
        return;
      }

      window.speechSynthesis.cancel();

      if (
        isPlayingAudio &&
        currentPlayingMessageId === messageId
      ) {
        setIsPlayingAudio(false);
        setCurrentPlayingMessageId(null);
        return;
      }

      const utterance =
        new SpeechSynthesisUtterance(text);

      utterance.lang = lang;
      utterance.rate = rate;

      utterance.onstart = () => {
        setIsPlayingAudio(true);

        if (messageId) {
          setCurrentPlayingMessageId(messageId);
        }
      };

      utterance.onend = () => {
        setIsPlayingAudio(false);
        setCurrentPlayingMessageId(null);
      };

      utterance.onerror = () => {
        setIsPlayingAudio(false);
        setCurrentPlayingMessageId(null);
      };

      window.speechSynthesis.speak(utterance);
    },
    [
      isPlayingAudio,
      currentPlayingMessageId,
    ],
  );

  /* ==========================================================
     STOP AUDIO
     ========================================================== */

  const stopAudio = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    setIsPlayingAudio(false);
    setCurrentPlayingMessageId(null);
  }, []);

  /* ==========================================================
     EXTRACT OUTPUT TEXT
     ========================================================== */

  const extractAgentText = (
    result: BackendAgentResult | undefined,
  ): string => {
    if (!result) {
      return '';
    }

    const output = result.output;

    if (typeof output === 'string') {
      return output.trim();
    }

    if (!isBackendAgentOutput(output)) {
      return '';
    }

    if (
      typeof output.recommendation === 'string' &&
      output.recommendation.trim()
    ) {
      return output.recommendation.trim();
    }

    if (
      typeof output.answer === 'string' &&
      output.answer.trim()
    ) {
      return output.answer.trim();
    }

    if (
      Array.isArray(output.hits) &&
      output.hits.length > 0
    ) {
      return output.hits
        .filter(isRetrievalHit)
        .map((hit) => {
          if (
            typeof hit.chunk_text === 'string' &&
            hit.chunk_text.trim()
          ) {
            return hit.chunk_text.trim();
          }

          if (
            typeof hit.answer_context === 'string' &&
            hit.answer_context.trim()
          ) {
            return hit.answer_context.trim();
          }

          return '';
        })
        .filter(Boolean)
        .join('\n\n');
    }

    return '';
  };

  /* ==========================================================
     MAP CITATIONS
     ========================================================== */

  const mapCitations = (
    rawCitations: unknown,
  ): Citation[] => {
    if (!Array.isArray(rawCitations)) {
      return [];
    }

    return rawCitations
      .filter(isBackendCitation)
      .map(
        (
          citation: BackendCitation,
          index: number,
        ) => ({
          citation_id:
            citation.citation_id ??
            `cit-${index}`,

          source_title:
            citation.title ??
            citation.source_title ??
            'Agricultural Knowledge Source',

          authority:
            citation.authority,

          document_type:
            citation.document_type,

          page:
            (citation.page_number ??
              citation.page) ??
            undefined,

          snippet:
            citation.snippet,

          relevance_score:
            citation.confidence ??
            citation.relevance_score,
        }),
      );
  };

  /* ==========================================================
     EXTRACT BACKEND RESULTS
     ========================================================== */

  const extractBackendResults = (
    response: unknown,
  ): BackendAgentResult[] => {
    if (!isRecord(response)) {
      return [];
    }

    const rawResults = response.results;

    if (!Array.isArray(rawResults)) {
      return [];
    }

    return rawResults.filter(
      isBackendAgentResult,
    );
  };

  /* ==========================================================
     FIND RESULT
     ========================================================== */

  const findResultByAgent = (
    results: BackendAgentResult[],
    agentName: string,
  ): BackendAgentResult | undefined => {
    return results.find(
      (result) =>
        result.agent === agentName,
    );
  };

  /* ==========================================================
     BUILD EVIDENCE PACKAGE
     ========================================================== */

  const buildEvidencePackage = (
    results: BackendAgentResult[],
  ): EvidencePackage | undefined => {
    const retrievalResult =
      findResultByAgent(
        results,
        'knowledge_retrieval_agent',
      );

    if (!retrievalResult) {
      return undefined;
    }

    const output = retrievalResult.output;

    if (!isBackendAgentOutput(output)) {
      return undefined;
    }

    const hits = Array.isArray(output.hits)
      ? output.hits.filter(isRetrievalHit)
      : [];

    if (hits.length === 0) {
      return undefined;
    }

    const citations = mapCitations(
      retrievalResult.citations,
    );


    return {
      citations,
      confidence_breakdown: {
        retrieval:
          retrievalResult.confidence ?? 0,
      },
    };
  };

  /* ==========================================================
     SEND MESSAGE
     ========================================================== */

  const sendMessage = useCallback(
    async (
      content: UserMessageContent,
    ) => {
      const query =
        content.text?.trim() || '';

      if (
        !query &&
        !content.image &&
        !content.voice
      ) {
        return;
      }

      const userMessageId =
        `user-${Date.now()}`;

      const userMessage: ChatMessage = {
        id: userMessageId,
        role: 'user',
        timestamp: new Date().toISOString(),
        userContent: content,
      };

      setMessages((previous) => [
        ...previous,
        userMessage,
      ]);

      setIsProcessing(true);

      try {
        /* ======================================================
           IMAGE
           ====================================================== */

        if (content.image) {
          setStage(
            'analyzing_image',
            'Analyzing crop image...',
            1,
            4,
            crop
              ? `Crop context: ${crop}`
              : 'Crop context not specified',
          );

          try {
            await visionApi.uploadImage(
              content.image.file,
              content.image.cropHint || crop,
            );
          } catch (visionError) {
            console.error(
              'Vision upload failed:',
              visionError,
            );
          }
        }

        /* ======================================================
           VOICE
           ====================================================== */

        /*
         * The multimodal composer already captures the voice
         * attachment. The backend agent request is still the
         * authoritative agricultural reasoning path.
         *
         * Do not call a nonexistent voiceApi.transcribe()
         * method here.
         */
        if (content.voice) {
          setStage(
            'transcribing_voice',
            'Processing voice query...',
            1,
            4,
            content.language
              ? `Language: ${content.language}`
              : undefined,
          );
        }

        /* ======================================================
           UNDERSTANDING / PLANNING
           ====================================================== */

        setStage(
          'understanding_goal',
          'Understanding agricultural question...',
          1,
          4,
          crop
            ? `Crop context: ${crop}`
            : 'No crop context specified',
        );

        const queryGoal =
          query ||
          'Analyze the provided crop information and provide a grounded agricultural advisory.';

        /*
         * Explicit crop in the current question wins.
         * Otherwise use the active farmer crop.
         */
        const requestCrop =
          resolveCropForQuery(
            queryGoal,
            crop,
          );

        console.info(
          '[KrishiOS] Agent request context:',
          {
            query: queryGoal,
            crop: requestCrop,
            state,
            district,
            season,
          },
        );

        /* ======================================================
           RETRIEVAL
           ====================================================== */

        setStage(
          'retrieving_agricultural_sources',
          'Retrieving grounded agricultural evidence...',
          2,
          4,
          requestCrop
            ? `Retrieving evidence for ${requestCrop}`
            : 'Retrieving general agricultural evidence',
        );

        const agentRes =
          await agentApi.execute({
            goal: queryGoal,
            session_id:
              sessionIdRef.current,

            ...(requestCrop
              ? {
                  crop: requestCrop,
                }
              : {}),

            ...(state
              ? {
                  state,
                }
              : {}),

            ...(district
              ? {
                  district,
                }
              : {}),

            ...(season
              ? {
                  season,
                }
              : {}),
          });

        const results =
          extractBackendResults(agentRes);

        const retrievalResult =
          findResultByAgent(
            results,
            'knowledge_retrieval_agent',
          );

        const advisoryResult =
          findResultByAgent(
            results,
            'crop_advisory_agent',
          );

        /* ======================================================
           EVALUATION
           ====================================================== */

        setStage(
          'evaluating_evidence',
          'Evaluating retrieved agricultural evidence...',
          3,
          4,
          advisoryResult
            ? 'Crop advisory agent completed'
            : 'Using verified retrieval evidence',
        );

        let outputText =
          extractAgentText(
            advisoryResult,
          );

        if (!outputText) {
          outputText =
            extractAgentText(
              retrievalResult,
            );
        }

        if (!outputText) {
          outputText =
            'I do not have enough verified information to provide a grounded recommendation for this question.';
        }

        const allCitations =
          results.flatMap(
            (result) =>
              Array.isArray(
                result.citations,
              )
                ? result.citations
                : [],
          );

        const citations =
          mapCitations(
            allCitations,
          );

        const confidence =
          advisoryResult?.confidence ??
          retrievalResult?.confidence ??
          0;

        const grounded =
          advisoryResult?.grounded ??
          retrievalResult?.grounded ??
          false;

        const evidence =
          buildEvidencePackage(
            results,
          );

        /* ======================================================
           RESPONSE VALIDATION
           ====================================================== */

        const validationResult =
          findResultByAgent(
            results,
            'response_validation_agent',
          );

        const validationOutput =
            validationResult &&
            isBackendAgentOutput(validationResult.output)
            ? validationResult.output
          : undefined;

        const validationPassed =
          typeof validationOutput?.passed ===
          'boolean'
            ? validationOutput.passed
            : undefined;

        /*
         * Backend validation remains authoritative.
         * Never bypass it in the frontend.
         */
        if (validationPassed === false) {
  const validatedText =
    validationOutput?.validated_text;

  outputText =
    typeof validatedText === 'string'
      ? validatedText
      : 'I do not have enough verified information.';
}

        /* ======================================================
           COMPLETE
           ====================================================== */

        setStage(
          'complete',
          'Advisory ready',
          4,
          4,
          requestCrop
            ? `Analysis completed for ${requestCrop}`
            : undefined,
        );

        /* ======================================================
           ASSISTANT MESSAGE
           ====================================================== */

        const assistantMessage: ChatMessage = {
  id: `assistant-${Date.now()}`,

  role: 'assistant',

  timestamp: new Date().toISOString(),

  aiContent: {
    text: outputText,
    confidence,
    grounded,
    citations,
    evidence,
    evaluation: {
      policyCompliant:
        validationPassed ?? true,
    },
  },
};

        setMessages(
          (previous) => [
            ...previous,
            assistantMessage,
          ],
        );
      } catch (error) {
        console.error(
          'AI conversation execution failed:',
          error,
        );

        setMessages(
          (previous) => [
            ...previous,
            {
              id:
                `assistant-error-${Date.now()}`,

              role: 'assistant',

              timestamp:
                new Date().toISOString(),

              aiContent: {
                text:
                  'Unable to complete the agricultural analysis right now. Please try again.',

                confidence: 0,

                grounded: false,

                citations: [],
              },
            },
          ],
        );

        setStage(
          'error',
          'Analysis failed',
          4,
          4,
          'Please try again.',
        );
      } finally {
        setIsProcessing(false);

        window.setTimeout(() => {
          setActiveStage(null);
        }, 500);
      }
    },
    [
      crop,
      state,
      district,
      season,
      setStage,
    ],
  );

  /* ==========================================================
     RESET
     ========================================================== */

  const resetConversation =
    useCallback(() => {
      setMessages([]);
      setActiveStage(null);
      setIsProcessing(false);
      stopAudio();

      sessionIdRef.current =
        `session-${Date.now()}`;
    }, [stopAudio]);

  /* ==========================================================
    WEATHER
     ========================================================== */

  const getWeatherContext =
    useCallback(async () => {
      try {
        return await weatherApi.getCurrentWeather({
          district,
          state,
        });
      } catch (error) {
        console.error(
          'Weather context fetch failed:',
          error,
        );

        return undefined;
      }
    }, [district, state]);

  /* ==========================================================
  RETURN API
     ========================================================== */

  return {
    messages,

    activeStage,

    isProcessing,

    isPlayingAudio,

    currentPlayingMessageId,

    sendMessage,

    resetConversation,

    speakText,

    stopAudio,

    getWeatherContext,

    initialSuggestions:
      getInitialSuggestions(crop),
  };
}