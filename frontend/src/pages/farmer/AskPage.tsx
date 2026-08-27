/**
 * AskPage Component (/farmer/ask).
 *
 * Primary multimodal AI Decision Support page for KrishiOS.
 * Accepts Text, Voice, and Crop Image inputs; executes Agent Runtime;
 * presents grounded agricultural advisories with full evidence provenance.
 */

import React, { useRef, useEffect } from 'react';
import { useAIConversation } from '@/features/ai/hooks/useAIConversation';
import { MultimodalComposer } from '@/features/ai/components/MultimodalComposer';
import { RichAIMessage } from '@/features/ai/components/RichAIMessage';
import { UserMessageBubble } from '@/features/ai/components/UserMessageBubble';
import { StageThinkingIndicator } from '@/features/ai/components/StageThinkingIndicator';
import { useFarmerProfile } from '@/features/farmer/hooks/useFarmerData';
import {
  Sparkles,
  RotateCcw,
  Bot,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';

export const AskPage: React.FC = () => {
  const { data: farmer } = useFarmerProfile();

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
  } = useAIConversation();

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeStage]);

  const farmContext = `${farmer?.full_name || 'Ramesh Patel'} • ${farmer?.landholding_acres || '4.5'} Ac Paddy (${farmer?.village || 'Khammam'})`;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-5xl mx-auto -my-4 sm:-my-6 bg-surface">
      {/* Top Header */}
      <header className="px-4 py-3 border-b border-border bg-surface flex items-center justify-between shrink-0 shadow-xs">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary-100 text-primary-700 flex items-center justify-center">
            <Sparkles className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-body font-bold text-text flex items-center gap-2">
              <span>Ask KrishiOS Intelligence</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-success-50 text-success-700 border border-success-200">
                Agent Runtime v10
              </span>
            </h1>
            <p className="text-caption text-text-muted">
              Multimodal Decision Intelligence for Indian Agriculture
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={resetConversation}
            className="cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
            <span>New Chat</span>
          </Button>
        )}
      </header>

      {/* Main Conversation Stream */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          /* Empty / Welcome State */
          <div className="max-w-2xl mx-auto py-8 text-center space-y-6 animate-fadeIn">
            <div className="w-16 h-16 rounded-2xl bg-primary-50 border border-primary-200 text-primary-600 flex items-center justify-center mx-auto shadow-sm">
              <Bot className="w-9 h-9" aria-hidden="true" />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-heading font-extrabold text-text tracking-tight">
                Namaste! How can KrishiOS assist your farm today?
              </h2>
              <p className="text-small text-text-secondary max-w-lg mx-auto">
                Ask in Telugu, Hindi, or English using voice or text. You can also attach photos of affected leaves or pests.
              </p>
            </div>

            {/* Quick Starter Suggestions */}
            <div className="space-y-2 text-left pt-2">
              <span className="text-caption font-bold text-text-muted uppercase block px-1">
                Suggested Questions:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {initialSuggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => sendMessage({ text: suggestion, language: 'te' })}
                    className="p-3 rounded-xl bg-surface border border-border hover:border-primary-400 hover:bg-primary-50/40 text-small text-text font-medium text-left transition-all cursor-pointer shadow-xs flex items-start justify-between gap-2"
                  >
                    <span>{suggestion}</span>
                    <Zap className="w-3.5 h-3.5 text-primary-600 shrink-0 mt-0.5" aria-hidden="true" />
                  </button>
                ))}
              </div>
            </div>

            {/* Trust and Safety Banner */}
            <div className="p-3 rounded-xl bg-surface-raised border border-border text-caption text-text-secondary flex items-center justify-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary-600 shrink-0" aria-hidden="true" />
              <span>Grounded in ICAR standard packages of practice &amp; live weather telemetry</span>
            </div>
          </div>
        ) : (
          /* Render Messages */
          messages.map((msg) => {
            if (msg.role === 'user' && msg.userContent) {
              return (
                <UserMessageBubble
                  key={msg.id}
                  content={msg.userContent}
                  timestamp={msg.timestamp}
                />
              );
            }

            if (msg.role === 'assistant' && msg.aiContent) {
              return (
                <RichAIMessage
                  key={msg.id}
                  messageId={msg.id}
                  content={msg.aiContent}
                  timestamp={msg.timestamp}
                  isPlayingAudio={isPlayingAudio && currentPlayingMessageId === msg.id}
                  onSpeak={speakText}
                  onStopAudio={stopAudio}
                  onSelectFollowUp={(prompt) => sendMessage({ text: prompt })}
                />
              );
            }

            return null;
          })
        )}

        {/* Multi-stage Thinking Indicator */}
        {activeStage && <StageThinkingIndicator stageInfo={activeStage} />}

        <div ref={messagesEndRef} />
      </main>

      {/* Multimodal Input Composer */}
      <MultimodalComposer
        onSend={sendMessage}
        disabled={isProcessing}
        farmContextLabel={farmContext}
      />
    </div>
  );
};

export default AskPage;
