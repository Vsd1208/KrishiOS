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
import { asAnalysisLanguage } from '@/services/api/assistant';
import { useDocumentAnalysis } from '@/features/assistant/useDocumentAnalysis';
import type { BotLanguage } from '@/services/api/conversation';
import { FarmerChat } from '@/features/conversation/FarmerChat';
import { useTranslation } from 'react-i18next';
import i18n from '@/i18n';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

/* ============================================================
   COMPONENT
   ============================================================ */

const BOT_LANGUAGES: BotLanguage[] = ['te', 'hi', 'en'];

/** Default view: the multilingual chat. The analyst workspace stays one click away. */
export const AskPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: farmer } = useFarmerProfile();
  const { crops, fieldCrops } = useFarmerCrops();
  const [mode, setMode] = useState<'chat' | 'workspace'>('chat');
  const [params] = useSearchParams();
  const location = useLocation();
  const bulletinUuid = params.get('bulletin');
  const bulletinTitle = (location.state as { bulletinTitle?: string } | null)?.bulletinTitle;

  const preferred = (farmer?.preferred_language || '').slice(0, 2).toLowerCase();
  const initialLanguage = (BOT_LANGUAGES as string[]).includes(preferred)
    ? (preferred as BotLanguage)
    : 'en';
  const profileCrops = crops
    .filter((c) => fieldCrops.some((fc) => fc.crop_id === c.id))
    .map((c) => (c.crop_name || c.name || '').trim().toLowerCase())
    .filter(Boolean);

  return (
    <div className="flex flex-col flex-1 h-full min-h-0 w-full">
      <div className="flex justify-end gap-1 pb-2" role="tablist">
        {(['chat', 'workspace'] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={`px-3 py-1 rounded-lg text-caption font-semibold border cursor-pointer ${
              mode === m ? 'bg-surface text-text border-border shadow-xs' : 'text-text-muted border-transparent'
            }`}
          >
            {m === 'chat' ? t('chat.simpleChat') : t('chat.advancedWorkspace')}
          </button>
        ))}
      </div>
      {mode === 'chat' ? (
        <div className="flex-1 min-h-0 bg-surface rounded-2xl border border-border/80 shadow-card overflow-hidden">
          <FarmerChat
            key={`${initialLanguage}-${bulletinUuid ?? ''}`}
            initialLanguage={initialLanguage}
            bulletinUuid={bulletinUuid}
            bulletinTitle={bulletinTitle}
            profile={profileCrops.length ? { crops: profileCrops } : null}
          />
        </div>
      ) : (
        <AnalystWorkspace />
      )}
    </div>
  );
};

const AnalystWorkspace: React.FC = () => {
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

  const districtName = farmer?.village || undefined;
  const totalAcres = farmer?.landholding_acres || fields.reduce((acc, f) => acc + (f.area_acres || 0), 0);
  const farmContext = [
    farmer?.full_name,
    totalAcres ? `${Number(totalAcres).toFixed(1)} Ac` : null,
    activeCropName,
    districtName,
  ]
    .filter(Boolean)
    .join(' • ');

  /* ==========================================================
     UI STATE
     ========================================================== */

  const [viewMode, setViewMode] = useState<WorkspaceViewMode>('split');
  const [latestImage, setLatestImage] = useState<ImageAttachment | undefined>(undefined);
  const navigate = useNavigate();
  // Document help: the farmer's document is summarised on the KrishiOS server (not stored)
  const doc = useDocumentAnalysis();
  const [docMissing, setDocMissing] = useState(false);
  const docPhase = docMissing ? 'missing' : doc.phase;
  const docAhead = doc.ahead;
  const docResult = doc.result;
  const uploadingDocument = doc.busy;
  const resetDoc = () => {
    setDocMissing(false);
    doc.reset();
  };
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
    district: districtName,
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

  // Officer questions go through Help, which creates a real grievance ticket.
  const handleEscalate = (): void => {
    void navigate('/farmer/help');
  };

  const handleDocumentUpload = async (): Promise<void> => {
    if (!selectedDocument) {
      setDocMissing(true);
      return;
    }
    setDocMissing(false);
    await doc.analyze(selectedDocument, {
      audience: 'farmer',
      language: asAnalysisLanguage(i18n.language),
      crops: activeCropName ? [activeCropName.toLowerCase()] : undefined,
    });
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
              <span>{i18n.t('chat.advancedWorkspace')}</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Floating Live Context Pill */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-raised border border-border text-caption">
            <div className="flex items-center gap-1 text-primary-700 font-semibold">
              <Sprout className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{activeCropName || '—'}</span>
            </div>
            <span className="text-border-strong">•</span>
            <div className="flex items-center gap-1 text-text-secondary">
              <MapPin className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
              <span>{districtName ?? '—'}</span>
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
              title={i18n.t('workspace.stream')}
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>{i18n.t('workspace.stream')}</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded-lg text-caption font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                viewMode === 'split'
                  ? 'bg-surface text-text shadow-xs border border-border'
                  : 'text-text-muted hover:text-text'
              }`}
              title={i18n.t('workspace.split')}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>{i18n.t('workspace.split')}</span>
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
              <span>{i18n.t('workspace.newChat')}</span>
            </Button>
          )}
        </div>
      </header>


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
                    {i18n.t('workspace.welcome')}
                  </h2>
                  <p className="text-small text-text-secondary max-w-lg mx-auto leading-relaxed">
                    {i18n.t('workspace.welcomeHelp', { chat: i18n.t('chat.simpleChat') })}
                  </p>
                </div>

                {/* Quick Starter Suggestions */}
                <div className="space-y-2 text-left pt-2">
                  <span className="text-caption font-bold text-text-muted uppercase tracking-wider block px-1">
                    {i18n.t('answer.followUps')}
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {initialSuggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() =>
                          handleSendWrapper({
                            text: suggestion,
                            language: (['te', 'hi', 'en'] as const).find((l) => i18n.language?.startsWith(l)) ?? 'en',
                          })
                        }
                        disabled={isProcessing}
                        className="p-3 rounded-xl bg-surface border border-border hover:border-primary-400 hover:bg-primary-50/40 text-small text-text font-medium text-left transition-all cursor-pointer shadow-xs flex items-start justify-between gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span className="group-hover:text-primary-900">{suggestion}</span>
                        <Zap className="w-4 h-4 text-primary-600 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" aria-hidden="true" />
                      </button>
                    ))}
                  </div>
                </div>

                {/* What the answers are based on: only claims the system backs up */}
                <div className="p-3.5 rounded-xl bg-surface-raised border border-border text-caption text-text-secondary flex items-center justify-center gap-2 shadow-xs">
                  <ShieldCheck className="w-4 h-4 text-primary-600 shrink-0" aria-hidden="true" />
                  <span>{i18n.t('workspace.trust')}</span>
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
                    accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      setSelectedDocument(file || null);
                      resetDoc();
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
                      {uploadingDocument ? i18n.t('workspace.docReading') : i18n.t('workspace.summarise')}
                    </Button>

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowUploadPanel(false);
                        setSelectedDocument(null);
                        resetDoc();
                      }}
                    >
                      {i18n.t('common.cancel')}
                    </Button>
                  </div>
                </div>

                <p className="text-caption text-text-muted">{i18n.t('workspace.docPrivacy')}</p>

                {docPhase !== 'idle' && docPhase !== 'done' && (
                  <div
                    role="status"
                    className={`flex items-center gap-1.5 text-caption ${
                      docPhase === 'failed' || docPhase === 'missing'
                        ? 'text-danger-700 font-medium'
                        : 'text-text-muted'
                    }`}
                  >
                    {docPhase === 'failed' || docPhase === 'missing' ? (
                      <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
                    ) : (
                      <Upload className="w-3.5 h-3.5" aria-hidden="true" />
                    )}
                    <span>
                      {docPhase === 'missing'
                        ? i18n.t('workspace.pickDoc')
                        : docPhase === 'failed'
                          ? i18n.t('workspace.docFailed')
                          : docPhase === 'queued' && docAhead > 0
                            ? i18n.t('workspace.docQueued', { count: docAhead })
                            : i18n.t('workspace.docWorking')}
                    </span>
                  </div>
                )}

                {docPhase === 'done' && docResult && (
                  <div className="rounded-xl border border-border bg-surface p-3 space-y-2" aria-live="polite">
                    <span className="flex items-center gap-1.5 text-caption font-semibold text-success-700">
                      <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                      {i18n.t('workspace.docSummary')}
                    </span>
                    <p className="text-small text-text whitespace-pre-line">{docResult.text}</p>
                    {docResult.translation_failed && (
                      <p className="text-caption text-text-muted">{i18n.t('workspace.docEnglish')}</p>
                    )}
                    {docResult.truncated && (
                      <p className="text-caption text-text-muted">
                        {i18n.t('workspace.docPartial', {
                          read: docResult.parts_read,
                          total: docResult.parts_total,
                        })}
                      </p>
                    )}
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
                {showUploadPanel ? i18n.t('workspace.closeUpload') : i18n.t('workspace.addDoc')}
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
