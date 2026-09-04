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
  useFarmerFields,
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
  MapPin,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Sprout,
  SunMedium,
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

  const { data: farmer } = useFarmerProfile();
  const { data: fields = [] } = useFarmerFields(farmer?.id);
  const { crops, fieldCrops } = useFarmerCrops();

  /* ==========================================================
     ACTIVE CROP & LOCATION
     ========================================================== */

  const activeFieldCrop = [...fieldCrops]
    .filter((fieldCrop) => ['Growing', 'Sown', 'Planned'].includes(fieldCrop.status))
    .sort((a, b) => {
      const statusRank: Record<string, number> = { Growing: 0, Sown: 1, Planned: 2 };
      return (statusRank[a.status] ?? 99) - (statusRank[b.status] ?? 99);
    })[0];

  const activeCropRecord = crops.find((c) => c.id === activeFieldCrop?.crop_id);

  const activeCropName =
    activeCropRecord?.crop_name?.trim() ||
    activeCropRecord?.name?.trim() ||
    undefined;

  const districtName = farmer?.village || 'Khammam';
  const totalAcres = farmer?.landholding_acres || fields.reduce((acc, f) => acc + (f.area_acres || 0), 0) || 4.5;
  const farmContext = `${farmer?.full_name || 'Farmer'} • ${Number(totalAcres).toFixed(1)} Ac ${activeCropName || 'Crop'} (${districtName})`;

  /* ==========================================================
     UI STATE
     ========================================================== */

  const [viewMode, setViewMode] = useState<WorkspaceViewMode>('split');
  const [latestImage, setLatestImage] = useState<ImageAttachment | undefined>(undefined);
  const [escalationNotice, setEscalationNotice] = useState<string | null>(null);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [documentUploadStatus, setDocumentUploadStatus] = useState<string | null>(null);
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<File | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

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
    district: districtName,
    season: 'Kharif',
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeStage]);

  const handleSendWrapper = (content: UserMessageContent): void => {
    if (content.image) {
      setLatestImage(content.image);
    }
    void sendMessage(content);
  };

  const handleEscalate = (): void => {
    setEscalationNotice(
      'Your inquiry has been submitted to the Mandal Agricultural Officer review queue.',
    );
    window.setTimeout(() => {
      setEscalationNotice(null);
    }, 5000);
  };

  const handleDocumentUpload = async (): Promise<void> => {
    if (!selectedDocument) {
      setDocumentUploadStatus('Please select a document first.');
      return;
    }

    setUploadingDocument(true);
    setDocumentUploadStatus(null);

    try {
      await documentsApi.upload(selectedDocument, {
        crop: activeCropName?.toLowerCase(),
        state: 'Telangana',
        district: farmer?.village || undefined,
        season: 'Kharif',
      });

      setDocumentUploadStatus('Document uploaded successfully.');
      setSelectedDocument(null);
      setShowUploadPanel(false);
    } catch (error) {
      console.error('Document upload failed:', error);
      setDocumentUploadStatus(
        error instanceof Error ? error.message : 'Document upload failed. Please try again.',
      );
    } finally {
      setUploadingDocument(false);
    }
  };

  const latestAIMessage = [...messages].reverse().find((m) => m.role === 'assistant')?.aiContent;

  return (
    <div className="flex flex-col flex-1 h-full min-h-0 w-full bg-surface rounded-2xl overflow-hidden border border-border/80 shadow-card">
      {/* Top Header */}
      <header className="px-4 py-3 border-b border-border/80 bg-surface flex items-center justify-between shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-600 to-primary-700 text-white flex items-center justify-center shadow-sm shadow-primary-600/20">
            <Sparkles className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-body font-bold text-text flex items-center gap-2">
              <span>Multimodal AI Intelligence Workspace</span>
              <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold bg-success-50 text-success-700 border border-success-200">
                Agent Runtime v10
              </span>
            </h1>
            <div className="flex items-center gap-2 text-caption text-text-muted mt-0.5">
              <span>GraphRAG • CropNet Vision • ICAR Provenance</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Floating Live Context Pill */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-raised border border-border text-caption">
            <div className="flex items-center gap-1 text-primary-700 font-semibold">
              <Sprout className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{activeCropName || 'Crop'}</span>
            </div>
            <span className="text-border-strong">•</span>
            <div className="flex items-center gap-1 text-text-secondary">
              <MapPin className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
              <span>{districtName}</span>
            </div>
            <span className="text-border-strong">•</span>
            <div className="flex items-center gap-1 text-amber-700 font-medium">
              <SunMedium className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Kharif</span>
            </div>
          </div>

          {/* Workspace Layout Switcher (Desktop) */}
          <div className="hidden lg:flex items-center gap-1 p-1 rounded-xl bg-surface-raised border border-border">
            <button
              type="button"
              onClick={() => setViewMode('stream')}
              className={`px-2.5 py-1 rounded-lg text-caption font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                viewMode === 'stream'
                  ? 'bg-surface text-text shadow-xs border border-border'
                  : 'text-text-muted hover:text-text'
              }`}
              title="Stream view"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Stream</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded-lg text-caption font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                viewMode === 'split'
                  ? 'bg-surface text-text shadow-xs border border-border'
                  : 'text-text-muted hover:text-text'
              }`}
              title="Split dual-pane canvas"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Split Canvas</span>
            </button>
          </div>

          {messages.length > 0 && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={resetConversation}
              className="cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
              <span>New Chat</span>
            </Button>
          )}
        </div>
      </header>

      {/* Escalation Notice */}
      {escalationNotice && (
        <div className="bg-primary-50 border-b border-primary-200 px-4 py-2.5 text-caption text-primary-900 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2 font-medium">
            <ShieldCheck className="w-4 h-4 text-primary-700 shrink-0" />
            <span>{escalationNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setEscalationNotice(null)}
            className="text-primary-700 font-bold hover:underline cursor-pointer ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Dual-Pane Workspace Container */}
      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 bg-surface">
        {/* Left Pane: Conversation Stream */}
        <div
          className={
            viewMode === 'split'
              ? 'lg:col-span-7 flex flex-col min-h-0 overflow-hidden border-r border-border'
              : 'lg:col-span-12 flex flex-col min-h-0 overflow-hidden'
          }
        >
          {/* Messages Stream */}
          <main className="flex-1 min-h-0 overflow-y-auto px-4 py-5 sm:px-6 space-y-6">
            {messages.length === 0 ? (
              /* Empty / Welcome Hero State */
              <div className="max-w-2xl mx-auto py-6 sm:py-8 text-center space-y-6 animate-fadeIn">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-50 to-primary-100/80 border border-primary-200 text-primary-600 flex items-center justify-center mx-auto shadow-sm">
                  <Bot className="w-9 h-9" aria-hidden="true" />
                </div>

                <div className="space-y-2">
                  <h2 className="text-heading font-extrabold text-text tracking-tight">
                    Namaste! How can KrishiOS assist your farm today?
                  </h2>
                  <p className="text-small text-text-secondary max-w-lg mx-auto leading-relaxed">
                    Ask in Telugu, Hindi, or English using voice or text. You can also attach photos of affected crop leaves for instant diagnostic analysis.
                  </p>
                </div>

                {/* Quick Starter Suggestions */}
                <div className="space-y-2 text-left pt-2">
                  <span className="text-caption font-bold text-text-muted uppercase tracking-wider block px-1">
                    Suggested Questions {activeCropName ? `for ${activeCropName}` : ''}:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {initialSuggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendWrapper({ text: suggestion, language: 'te' })}
                        disabled={isProcessing}
                        className="p-3 rounded-xl bg-surface border border-border hover:border-primary-400 hover:bg-primary-50/40 text-small text-text font-medium text-left transition-all cursor-pointer shadow-xs flex items-start justify-between gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span className="group-hover:text-primary-900">{suggestion}</span>
                        <Zap className="w-4 h-4 text-primary-600 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" aria-hidden="true" />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Trust and Safety Banner */}
                <div className="p-3.5 rounded-xl bg-surface-raised border border-border text-caption text-text-secondary flex items-center justify-center gap-2 shadow-xs">
                  <ShieldCheck className="w-4 h-4 text-primary-600 shrink-0" aria-hidden="true" />
                  <span>Grounded in ICAR standard packages of practice &amp; live agromet telemetry</span>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => {
                  if (message.role === 'user' && message.userContent) {
                    return (
                      <UserMessageBubble
                        key={message.id}
                        content={message.userContent}
                        timestamp={message.timestamp}
                      />
                    );
                  }

                  if (message.role === 'assistant' && message.aiContent) {
                    return (
                      <RichAIMessage
                        key={message.id}
                        messageId={message.id}
                        content={message.aiContent}
                        timestamp={message.timestamp}
                        isPlayingAudio={isPlayingAudio && currentPlayingMessageId === message.id}
                        onSpeak={speakText}
                        onStopAudio={stopAudio}
                        onSelectFollowUp={(prompt) => handleSendWrapper({ text: prompt })}
                        onEscalate={handleEscalate}
                        crop={activeCropName}
                      />
                    );
                  }

                  return null;
                })}

                {activeStage && <StageThinkingIndicator stageInfo={activeStage} />}

                <div ref={messagesEndRef} />
              </div>
            )}
          </main>

          {/* Document Upload Panel */}
          {showUploadPanel && (
            <div className="shrink-0 border-t border-border bg-surface-raised px-4 py-3">
              <div className="flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      setSelectedDocument(file || null);
                      setDocumentUploadStatus(null);
                    }}
                    className="block w-full text-sm text-text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100"
                  />

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleDocumentUpload}
                      disabled={uploadingDocument || !selectedDocument}
                    >
                      <Upload className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />
                      {uploadingDocument ? 'Uploading...' : 'Upload'}
                    </Button>

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowUploadPanel(false);
                        setSelectedDocument(null);
                        setDocumentUploadStatus(null);
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
                        : documentUploadStatus.includes('successfully')
                          ? 'text-success-700 font-medium'
                          : 'text-danger-700 font-medium'
                    }`}
                  >
                    {uploadingDocument ? (
                      <Upload className="w-3.5 h-3.5" aria-hidden="true" />
                    ) : documentUploadStatus.includes('successfully') ? (
                      <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
                    )}
                    <span>{documentUploadStatus}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Composer Footer */}
          <div className="shrink-0 border-t border-border bg-surface">
            <div className="flex items-center justify-end px-4 pt-1.5">
              <button
                type="button"
                onClick={() => setShowUploadPanel((value) => !value)}
                className="text-caption text-text-muted hover:text-primary-700 transition-colors cursor-pointer"
              >
                {showUploadPanel ? 'Close document upload' : '+ Add knowledge document'}
              </button>
            </div>

            <MultimodalComposer
              onSend={handleSendWrapper}
              disabled={isProcessing || uploadingDocument}
              farmContextLabel={farmContext}
              crop={activeCropName}
            />
          </div>
        </div>

        {/* Right Pane: Intelligence Canvas */}
        {viewMode === 'split' && (
          <div className="hidden lg:block lg:col-span-5 h-full overflow-hidden p-2.5 bg-surface-raised/40">
            <IntelligenceCanvas
              activeAIContent={latestAIMessage}
              latestUserImage={latestImage}
              crop={activeCropName}
              district={districtName}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default AskPage;
