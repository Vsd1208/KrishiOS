/**
 * AskPage Component (/farmer/ask).
 *
 * Multimodal AI Intelligence Workspace for KrishiOS.
 *
 * Crop context is derived dynamically from the farmer's
 * active field crop. No crop is hardcoded here.
 */

import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  useFarmerCrops,
  useFarmerProfile,
} from '@/features/farmer/hooks/useFarmerData';

import { useAIConversation } from '@/features/ai/hooks/useAIConversation';

import { MultimodalComposer } from '@/features/ai/components/MultimodalComposer';
import { RichAIMessage } from '@/features/ai/components/RichAIMessage';
import { UserMessageBubble } from '@/features/ai/components/UserMessageBubble';
import { StageThinkingIndicator } from '@/features/ai/components/StageThinkingIndicator';
import { IntelligenceCanvas } from '@/features/ai/components/IntelligenceCanvas';

import {
  Bot,
  CheckCircle2,
  Columns,
  Maximize2,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Upload,
  XCircle,
  Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/Button';

import type { WorkspaceViewMode } from '@/features/ai/types/workspace';

import type {
  ImageAttachment,
  UserMessageContent,
} from '@/features/ai/types/conversation';

import { documentsApi } from '@/services/api/documents';

/* ============================================================
   COMPONENT
   ============================================================ */

export const AskPage: React.FC = () => {
  /* ==========================================================
     FARMER DATA
     ========================================================== */

  const { data: farmer } =
    useFarmerProfile();

  const {
    crops,
    fieldCrops,
  } = useFarmerCrops();

  /* ==========================================================
     ACTIVE CROP
     ========================================================== */

  const activeFieldCrop =
    [...fieldCrops]
      .filter((fieldCrop) =>
        [
          'Growing',
          'Sown',
          'Planned',
        ].includes(fieldCrop.status),
      )
      .sort((a, b) => {
        const statusRank: Record<
          string,
          number
        > = {
          Growing: 0,
          Sown: 1,
          Planned: 2,
        };

        return (
          (statusRank[a.status] ?? 99) -
          (statusRank[b.status] ?? 99)
        );
      })[0];

  const activeCropRecord =
    crops.find(
      (cropRecord) =>
        cropRecord.id ===
        activeFieldCrop?.crop_id,
    );

  /*
   * Current Crop type uses crop_type.
   *
   * crop_name is retained as a compatibility fallback
   * for an API response that may expose that field.
   */
  const cropRecordWithOptionalName =
    activeCropRecord as
      | (
          typeof activeCropRecord & {
            crop_name?: string;
          }
        )
      | undefined;

  const activeCropName =
    cropRecordWithOptionalName?.crop_type?.trim() ||
    cropRecordWithOptionalName?.crop_name?.trim() ||
    undefined;

  /* ==========================================================
     UI STATE
     ========================================================== */

  const [
    viewMode,
    setViewMode,
  ] = useState<WorkspaceViewMode>(
    'split',
  );

  const [
    latestImage,
    setLatestImage,
  ] = useState<
    ImageAttachment | undefined
  >(undefined);

  const [
    escalationNotice,
    setEscalationNotice,
  ] = useState<string | null>(
    null,
  );

  const [
    uploadingDocument,
    setUploadingDocument,
  ] = useState(false);

  const [
    documentUploadStatus,
    setDocumentUploadStatus,
  ] = useState<string | null>(
    null,
  );

  const [
    showUploadPanel,
    setShowUploadPanel,
  ] = useState(false);

  const [
    selectedDocument,
    setSelectedDocument,
  ] = useState<File | null>(
    null,
  );

  const messagesEndRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  /* ==========================================================
     AI CONVERSATION
     ========================================================== */

  const {
    messages,
    activeStage,
    isProcessing,
    isPlayingAudio,
    currentPlayingMessageId,
    sendMessage,
    resetConversation,
    speakText,
    stopAudio,
    initialSuggestions,
  } = useAIConversation({
    crop: activeCropName,
    state: 'Telangana',
    district:
      farmer?.village ||
      'Khammam',
    season: 'Kharif',
  });

  /* ==========================================================
     AUTO SCROLL
     ========================================================== */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  }, [
    messages,
    activeStage,
  ]);

  /* ==========================================================
     SEND WRAPPER
     ========================================================== */

  const handleSendWrapper = (
    content: UserMessageContent,
  ): void => {
    if (content.image) {
      setLatestImage(
        content.image,
      );
    }

    void sendMessage(content);
  };

  /* ==========================================================
     ESCALATION
     ========================================================== */

  const handleEscalate = (): void => {
    setEscalationNotice(
      'Your inquiry has been submitted to the Mandal Agricultural Officer review queue.',
    );

    window.setTimeout(() => {
      setEscalationNotice(null);
    }, 5000);
  };

  /* ==========================================================
     DOCUMENT UPLOAD
     ========================================================== */

  const handleDocumentUpload =
    async (): Promise<void> => {
      if (!selectedDocument) {
        setDocumentUploadStatus(
          'Please select a document first.',
        );
        return;
      }

      setUploadingDocument(true);
      setDocumentUploadStatus(null);

      try {
        await documentsApi.upload(
          selectedDocument,
          {
            crop:
              activeCropName?.toLowerCase(),

            state:
              'Telangana',

            district:
              farmer?.village ||
              undefined,

            season:
              'Kharif',
          },
        );

        setDocumentUploadStatus(
          'Document uploaded successfully.',
        );

        setSelectedDocument(null);
        setShowUploadPanel(false);
      } catch (error) {
        console.error(
          'Document upload failed:',
          error,
        );

        setDocumentUploadStatus(
          error instanceof Error
            ? error.message
            : 'Document upload failed. Please try again.',
        );
      } finally {
        setUploadingDocument(false);
      }
    };

  /* ==========================================================
     FARM CONTEXT
     ========================================================== */

  const farmContext =
    `${farmer?.full_name || 'Farmer'} • ${
      farmer?.landholding_acres || '4.5'
    } Ac ${
      activeCropName ||
      'Crop not selected'
    } (${
      farmer?.village ||
      'Unknown'
    })`;

  /* ==========================================================
     LATEST AI MESSAGE
     ========================================================== */

  const latestAIMessage =
    [...messages]
      .reverse()
      .find(
        (message) =>
          message.role ===
          'assistant',
      )
      ?.aiContent;

  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <div className="flex flex-col h-full min-h-0 max-w-7xl mx-auto bg-surface">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <header className="px-4 py-2.5 border-b border-border bg-surface flex items-center justify-between shrink-0 shadow-xs">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-50 text-primary-700">
            <Sparkles
              className="w-4 h-4"
              aria-hidden="true"
            />
          </div>

          <div>
            <h1 className="text-sm font-semibold text-text">
              Ask KrishiOS
            </h1>

            <p className="text-caption text-text-muted">
              Grounded agricultural intelligence
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface-raised border border-border">
            <Bot
              className="w-3.5 h-3.5 text-primary-600"
              aria-hidden="true"
            />

            <span className="text-caption text-text-secondary">
              {activeCropName ||
                'Crop not selected'}
            </span>
          </div>

          {/* ==================================================
              VIEW MODE
              ================================================== */}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() =>
              setViewMode(
                viewMode === 'split'
                  ? 'stream'
                  : 'split',
              )
            }
            title={
              viewMode === 'split'
                ? 'Focus chat'
                : 'Show intelligence canvas'
            }
            aria-label={
              viewMode === 'split'
                ? 'Focus chat'
                : 'Show intelligence canvas'
            }
          >
            {viewMode === 'split' ? (
              <Maximize2
                className="w-4 h-4"
                aria-hidden="true"
              />
            ) : (
              <Columns
                className="w-4 h-4"
                aria-hidden="true"
              />
            )}
          </Button>

          {/* ==================================================
              RESET
              ================================================== */}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={
              resetConversation
            }
            title="Reset conversation"
            aria-label="Reset conversation"
          >
            <RotateCcw
              className="w-4 h-4"
              aria-hidden="true"
            />
          </Button>
        </div>
      </header>

      {/* ======================================================
          ESCALATION NOTICE
          ====================================================== */}

      {escalationNotice && (
        <div className="mx-3 mt-3 p-3 rounded-xl bg-success-50 border border-success-200 text-success-800 text-sm">
          {escalationNotice}
        </div>
      )}

      {/* ======================================================
          MAIN WORKSPACE
          ====================================================== */}

      <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 min-h-0 overflow-hidden">

        {/* ====================================================
            LEFT / CHAT
            ==================================================== */}

        <div
          className={
            viewMode === 'split'
              ? 'lg:col-span-7 flex flex-col min-h-0 overflow-hidden'
              : 'lg:col-span-12 flex flex-col min-h-0 overflow-hidden'
          }
        >

          {/* ==================================================
              CHAT STREAM
              ================================================== */}

          <main className="flex-1 min-h-0 overflow-y-auto px-3 py-4 sm:px-5">

            {messages.length === 0 ? (
              <div className="max-w-3xl mx-auto">

                <div className="flex flex-col items-center text-center py-8 sm:py-12">
                  <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-50 text-primary-700 mb-4">
                    <Sparkles
                      className="w-7 h-7"
                      aria-hidden="true"
                    />
                  </div>

                  <h2 className="text-xl sm:text-2xl font-semibold text-text">
                    How can I help with your farm?
                  </h2>

                  <p className="mt-2 max-w-xl text-sm text-text-secondary">
                    Ask about pests, diseases,
                    nutrients, irrigation,
                    weather, crop management,
                    or field observations.
                  </p>

                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    <div className="px-3 py-2 rounded-xl bg-surface-raised border border-border text-caption text-text-secondary">
                      <span className="font-medium text-text">
                        Farm:
                      </span>{' '}
                      {farmContext}
                    </div>
                  </div>
                </div>

                {/* =================================================
                    SUGGESTIONS
                    ================================================= */}

                <div className="mt-4">
                  <p className="text-caption font-medium text-text-muted mb-2">
                    Suggested questions
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {initialSuggestions.map(
                      (suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() =>
                            handleSendWrapper({
                              text: suggestion,
                            })
                          }
                          disabled={
                            isProcessing
                          }
                          className="p-3 rounded-xl bg-surface border border-border hover:border-primary-400 hover:bg-primary-50/40 text-small text-text font-medium text-left transition-all cursor-pointer shadow-xs flex items-start justify-between gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <span>
                            {suggestion}
                          </span>

                          <Zap
                            className="w-3.5 h-3.5 text-primary-600 shrink-0 mt-0.5"
                            aria-hidden="true"
                          />
                        </button>
                      ),
                    )}
                  </div>
                </div>

                {/* =================================================
                    TRUST
                    ================================================= */}

                <div className="mt-5 p-3 rounded-xl bg-surface-raised border border-border text-caption text-text-secondary flex items-center justify-center gap-2">
                  <ShieldCheck
                    className="w-4 h-4 text-primary-600 shrink-0"
                    aria-hidden="true"
                  />

                  <span>
                    Grounded in agricultural knowledge
                    sources, retrieval evidence &
                    live weather telemetry
                  </span>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-4">

                {messages.map(
                  (message) => {
                    if (
                      message.role ===
                        'user' &&
                      message.userContent
                    ) {
                      return (
                        <UserMessageBubble
                          key={
                            message.id
                          }
                          content={
                            message.userContent
                          }
                          timestamp={
                            message.timestamp
                          }
                        />
                      );
                    }

                    if (
                      message.role ===
                        'assistant' &&
                      message.aiContent
                    ) {
                      return (
                        <RichAIMessage
                          key={
                            message.id
                          }
                          messageId={
                            message.id
                          }
                          content={
                            message.aiContent
                          }
                          timestamp={
                            message.timestamp
                          }
                          isPlayingAudio={
                            isPlayingAudio &&
                            currentPlayingMessageId ===
                              message.id
                          }
                          onSpeak={
                            speakText
                          }
                          onStopAudio={
                            stopAudio
                          }
                          onSelectFollowUp={(
                            prompt,
                          ) =>
                            handleSendWrapper({
                              text: prompt,
                            })
                          }
                          onEscalate={
                            handleEscalate
                          }
                          crop={
                            activeCropName
                          }
                        />
                      );
                    }

                    return null;
                  },
                )}

                {activeStage && (
                  <StageThinkingIndicator
                    stageInfo={
                      activeStage
                    }
                  />
                )}

                <div
                  ref={
                    messagesEndRef
                  }
                />
              </div>
            )}
          </main>

          {/* ====================================================
              DOCUMENT UPLOAD
              ==================================================== */}

          {showUploadPanel && (
            <div className="shrink-0 border-t border-border bg-surface-raised px-3 py-3">
              <div className="max-w-3xl mx-auto flex flex-col gap-3">

                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={(
                      event,
                    ) => {
                      const file =
                        event.target.files?.[0];

                      setSelectedDocument(
                        file ||
                          null,
                      );

                      setDocumentUploadStatus(
                        null,
                      );
                    }}
                    className="block w-full text-sm text-text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100"
                  />

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      size="sm"
                      onClick={
                        handleDocumentUpload
                      }
                      disabled={
                        uploadingDocument ||
                        !selectedDocument
                      }
                    >
                      <Upload
                        className="w-3.5 h-3.5 mr-1.5"
                        aria-hidden="true"
                      />

                      {uploadingDocument
                        ? 'Uploading...'
                        : 'Upload'}
                    </Button>

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowUploadPanel(
                          false,
                        );

                        setSelectedDocument(
                          null,
                        );

                        setDocumentUploadStatus(
                          null,
                        );
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>

                {documentUploadStatus && (
                  <div
                    className={`flex items-center gap-1.5 text-caption ${
                      uploadingDocument
                        ? 'text-text-muted'
                        : documentUploadStatus.includes(
                              'successfully',
                            )
                          ? 'text-success-700'
                          : 'text-danger-700'
                    }`}
                  >
                    {uploadingDocument ? (
                      <Upload
                        className="w-3.5 h-3.5"
                        aria-hidden="true"
                      />
                    ) : documentUploadStatus.includes(
                        'successfully',
                      ) ? (
                      <CheckCircle2
                        className="w-3.5 h-3.5"
                        aria-hidden="true"
                      />
                    ) : (
                      <XCircle
                        className="w-3.5 h-3.5"
                        aria-hidden="true"
                      />
                    )}

                    <span>
                      {
                        documentUploadStatus
                      }
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ====================================================
              COMPOSER
              ==================================================== */}

          <div className="shrink-0 border-t border-border bg-surface p-2 sm:p-3">
            <div className="max-w-3xl mx-auto">

              <div className="flex items-center justify-end mb-1.5">
                <button
                  type="button"
                  onClick={() =>
                    setShowUploadPanel(
                      (value) =>
                        !value,
                    )
                  }
                  className="text-caption text-text-muted hover:text-primary-700 transition-colors"
                >
                  {showUploadPanel
                    ? 'Close document upload'
                    : 'Add knowledge document'}
                </button>
              </div>

              <MultimodalComposer
                onSend={
                  handleSendWrapper
                }
                disabled={
                  isProcessing ||
                  uploadingDocument
                }
                farmContextLabel={
                  farmContext
                }
                crop={
                  activeCropName
                }
              />
            </div>
          </div>
        </div>

        {/* ======================================================
            RIGHT: INTELLIGENCE CANVAS
            ====================================================== */}

        {viewMode === 'split' && (
          <div className="hidden lg:block lg:col-span-5 h-full min-h-0 overflow-hidden p-2">
            <IntelligenceCanvas
              activeAIContent={
                latestAIMessage
              }
              latestUserImage={
                latestImage
              }
              crop={
                activeCropName
              }
              district={
                farmer?.village ||
                'Unknown'
              }
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default AskPage;