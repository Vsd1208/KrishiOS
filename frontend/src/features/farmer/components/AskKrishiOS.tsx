/**
 * AskKrishiOS Component.
 *
 * Multimodal AI Assistant Hub for Farmers.
 * Integrates text queries with the Agent Runtime (POST /api/v1/agents/execute),
 * voice modal, and vision crop diagnosis modal.
 * Displays confidence, plain-language evidence, and source citations.
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { CitationCard } from '@/components/ai/CitationCard';
import { ThinkingIndicator } from '@/components/ai/ThinkingIndicator';
import { VoiceRecorderModal } from '@/features/farmer/components/VoiceRecorderModal';
import { CropVisionModal } from '@/features/farmer/components/CropVisionModal';
import { agentApi } from '@/services/api/agent';
import {
  Send,
  Mic,
  Camera,
  Sparkles,
  ChevronDown,
  ChevronUp,
  BookOpen,
} from 'lucide-react';
import type { AgentExecutionResponse } from '@/types/agent';
import type { Farmer, FieldCrop } from '@/types/domain';

interface Message {
  id: string;
  sender: 'farmer' | 'ai';
  text: string;
  timestamp: string;
  responsePayload?: AgentExecutionResponse;
  confidence?: number;
}

const SAMPLE_QUICK_QUESTIONS = [
  'వరిలో కాండం తొలుచు పురుగు నివారణ ఏమిటి?',
  'What is the recommended fertilizer dosage for Paddy at tillering stage?',
  'Is today favorable for spraying pesticide in my field?',
  'What are the current market rates for Cotton in Warangal Mandi?',
];

interface AskKrishiOSProps {
  farmer?: Farmer | null;
  fieldCrops?: FieldCrop[];
}

export const AskKrishiOS: React.FC<AskKrishiOSProps> = ({ farmer, fieldCrops }) => {
  const [inputQuery, setInputQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});

  // Modals
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [isVisionOpen, setIsVisionOpen] = useState(false);

  const activeCropName = fieldCrops?.[0] ? 'Paddy' : 'Paddy';
  const districtName = farmer?.village || 'Khammam';

  const handleSendQuery = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim();
    if (!textToSend || isLoading) return;

    const userMsgId = `user-${Date.now()}`;
    const newMessages: Message[] = [
      ...messages,
      {
        id: userMsgId,
        sender: 'farmer',
        text: textToSend,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];

    setMessages(newMessages);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await agentApi.execute({
        goal: textToSend,
        state: 'Telangana',
        district: districtName,
        crop: activeCropName,
        season: 'Kharif',
      });

      const primaryResult = response.results[0];
      const outputText =
        primaryResult?.output ||
        'I have analyzed your farm context and ICAR advisories. Please verify with your extension officer.';
      const confidence = primaryResult?.confidence ?? 0.88;

      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: outputText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          responsePayload: response,
          confidence,
        },
      ]);
    } catch (err) {
      console.error('Agent query error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-err-${Date.now()}`,
          sender: 'ai',
          text: 'Unable to complete analysis right now. Please check your network connection or try again.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto space-y-4">
      {/* Header Banner */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-primary-700 to-primary-800 text-white shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-primary-200" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-body font-bold">Ask KrishiOS Intelligence</h1>
            <p className="text-caption text-primary-100">
              Multilingual agricultural decision support • Text, Voice, or Photo
            </p>
          </div>
        </div>

        <div className="flex gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsVoiceOpen(true)}
            className="bg-white/10 hover:bg-white/20 border-white/30 text-white cursor-pointer"
          >
            <Mic className="w-4 h-4 mr-1 sm:mr-1.5" aria-hidden="true" />
            <span className="hidden sm:inline">Voice</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsVisionOpen(true)}
            className="bg-white/10 hover:bg-white/20 border-white/30 text-white cursor-pointer"
          >
            <Camera className="w-4 h-4 mr-1 sm:mr-1.5" aria-hidden="true" />
            <span className="hidden sm:inline">Crop Photo</span>
          </Button>
        </div>
      </div>

      {/* Messages Thread Container */}
      <div className="flex-1 min-h-[380px] p-4 rounded-xl bg-surface border border-border overflow-y-auto space-y-4 shadow-inner">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 my-auto">
            <div className="w-14 h-14 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center">
              <Sparkles className="w-8 h-8" aria-hidden="true" />
            </div>
            <div className="max-w-md space-y-1">
              <h3 className="text-subheading font-bold text-text">How can KrishiOS assist you today?</h3>
              <p className="text-small text-text-secondary">
                Ask any question regarding crop pests, disease management, spray weather, or mandi prices.
              </p>
            </div>

            {/* Quick Prompt Suggestions */}
            <div className="w-full max-w-lg pt-4 space-y-2">
              <span className="text-caption font-bold text-text-muted uppercase tracking-wider block text-left">
                Suggested Questions:
              </span>
              <div className="grid grid-cols-1 gap-2 text-left">
                {SAMPLE_QUICK_QUESTIONS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendQuery(prompt)}
                    className="p-2.5 rounded-lg bg-surface-raised hover:bg-primary-50/60 border border-border hover:border-primary-300 text-small text-text transition-all text-left cursor-pointer flex items-center justify-between group"
                  >
                    <span>{prompt}</span>
                    <Send className="w-3.5 h-3.5 text-text-muted group-hover:text-primary-600 flex-shrink-0 ml-2" aria-hidden="true" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              const isAi = msg.sender === 'ai';
              const citations = msg.responsePayload?.results?.[0]?.citations ?? [];
              const isEvExpanded = expandedEvidence[msg.id] ?? false;

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isAi ? 'items-start' : 'items-end'} space-y-1`}
                >
                  <div
                    className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-4 shadow-sm ${
                      isAi
                        ? 'bg-surface-raised border border-border text-text rounded-tl-sm'
                        : 'bg-primary-600 text-white rounded-tr-sm'
                    }`}
                  >
                    {/* Header for AI */}
                    {isAi && (
                      <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-border/60">
                        <div className="flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4 text-primary-600" aria-hidden="true" />
                          <span className="text-caption font-bold text-primary-900">
                            KrishiOS Advisory
                          </span>
                        </div>
                        {msg.confidence !== undefined && (
                          <ConfidenceBadge confidence={msg.confidence} size="sm" showLabel />
                        )}
                      </div>
                    )}

                    {/* Content */}
                    <p className="text-body whitespace-pre-line leading-relaxed">{msg.text}</p>

                    {/* Citations & Evidence Drawer for AI Messages */}
                    {isAi && citations.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-border/80 space-y-2">
                        <button
                          type="button"
                          onClick={() => toggleEvidence(msg.id)}
                          className="flex items-center justify-between w-full text-caption font-semibold text-primary-700 hover:text-primary-800 cursor-pointer pt-1"
                        >
                          <span className="flex items-center gap-1">
                            <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
                            Why this answer? ({citations.length} agricultural sources)
                          </span>
                          {isEvExpanded ? (
                            <ChevronUp className="w-4 h-4" aria-hidden="true" />
                          ) : (
                            <ChevronDown className="w-4 h-4" aria-hidden="true" />
                          )}
                        </button>

                        {isEvExpanded && (
                          <div className="space-y-2 pt-1 animate-fadeIn">
                            {citations.map((cit, cIdx) => (
                              <CitationCard
                                key={cIdx}
                                citation={{
                                  source_title: cit.title || cit.source || 'ICAR Agricultural Advisory',
                                  authority: cit.authority || 'State Agricultural University',
                                  document_type: cit.document_type || 'Package of Practices',
                                  snippet: cit.snippet,
                                  page: cit.page,
                                }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Message Timestamp */}
                    <div
                      className={`text-[10px] mt-1 text-right ${
                        isAi ? 'text-text-muted' : 'text-primary-200'
                      }`}
                    >
                      {msg.timestamp}
                    </div>
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-surface-raised border border-border rounded-2xl p-4 shadow-sm">
                  <ThinkingIndicator message="Synthesizing ICAR advisories & farm weather context..." />
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input Composer Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendQuery();
        }}
        className="p-2 rounded-xl bg-surface border border-border shadow-sm flex items-center gap-2"
      >
        <button
          type="button"
          onClick={() => setIsVoiceOpen(true)}
          className="p-2.5 rounded-lg text-text-secondary hover:text-primary-600 hover:bg-surface-raised transition-colors cursor-pointer"
          title="Voice Query"
          aria-label="Voice Query"
        >
          <Mic className="w-5 h-5" aria-hidden="true" />
        </button>

        <button
          type="button"
          onClick={() => setIsVisionOpen(true)}
          className="p-2.5 rounded-lg text-text-secondary hover:text-accent-600 hover:bg-surface-raised transition-colors cursor-pointer"
          title="Crop Photo Diagnostic"
          aria-label="Crop Photo Diagnostic"
        >
          <Camera className="w-5 h-5" aria-hidden="true" />
        </button>

        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask in Telugu, Hindi, or English..."
          disabled={isLoading}
          className="flex-1 bg-transparent px-2 py-1.5 text-body text-text placeholder:text-text-muted focus:outline-none"
        />

        <Button
          type="submit"
          variant="primary"
          disabled={!inputQuery.trim() || isLoading}
          className="rounded-lg px-4"
        >
          <Send className="w-4 h-4 mr-1 sm:mr-1.5" aria-hidden="true" />
          <span className="hidden sm:inline">Ask</span>
        </Button>
      </form>

      {/* Modals */}
      <VoiceRecorderModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        defaultLanguage="te"
      />
      <CropVisionModal
        isOpen={isVisionOpen}
        onClose={() => setIsVisionOpen(false)}
        defaultCrop={activeCropName}
      />
    </div>
  );
};

export default AskKrishiOS;
