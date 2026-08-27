/**
 * TypeScript types and view models for AI Decision Intelligence Conversation.
 */

import type { Citation, EvidencePackage, RiskSeverity } from '@/types/proactive';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ImageAttachment {
  file: File;
  previewUrl: string;
  cropHint?: string;
  analysisId?: number;
  analysisUuid?: string;
  diagnosisCondition?: string;
  diagnosisConfidence?: number;
}

export interface VoiceAttachment {
  audioBlob: Blob;
  durationSeconds: number;
  detectedLanguage?: string;
  transcript?: string;
}

export interface UserMessageContent {
  text: string;
  image?: ImageAttachment;
  voice?: VoiceAttachment;
  language?: 'te' | 'hi' | 'en';
}

export interface LiveContextSummary {
  temperatureCelsius?: number;
  weatherCondition?: string;
  sprayWindowFavorable?: boolean;
  sprayWindowReason?: string;
  mandiCommodity?: string;
  mandiModalPrice?: number;
}

export interface AIMessageContent {
  text: string;
  confidence?: number;
  grounded?: boolean;
  citations?: Citation[];
  evidence?: EvidencePackage;
  riskSeverity?: RiskSeverity;
  riskTitle?: string;
  liveContext?: LiveContextSummary;
  spokenAudioReference?: string;
  agentUsed?: string;
  suggestedFollowUps?: string[];
  evaluation?: {
    coherenceScore?: number;
    hallucinationDetected?: boolean;
    groundingRatio?: number;
    policyCompliant?: boolean;
  };
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  timestamp: string;
  userContent?: UserMessageContent;
  aiContent?: AIMessageContent;
  error?: string;
}

export type ProcessingStage =
  | 'idle'
  | 'recording_voice'
  | 'transcribing_voice'
  | 'analyzing_image'
  | 'understanding_goal'
  | 'retrieving_agricultural_sources'
  | 'evaluating_evidence'
  | 'synthesizing_advisory'
  | 'complete'
  | 'error';

export interface StageInfo {
  stage: ProcessingStage;
  message: string;
  detail?: string;
  stepNumber: number;
  totalSteps: number;
}
