/**
 * Workspace and session types for Multimodal AI Intelligence Workspace.
 */

import type { ChatMessage } from '@/features/ai/types/conversation';

export type WorkspaceViewMode = 'stream' | 'split' | 'canvas';

export type CanvasTab = 'graph' | 'telemetry' | 'vision' | 'provenance' | 'evaluation';

export interface ConsultationSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  crop?: string;
  district?: string;
  messages: ChatMessage[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'crop' | 'pest' | 'disease' | 'chemical' | 'practice' | 'constraint';
}

export interface GraphLink {
  source: string;
  target: string;
  relationship: string;
  confidence?: number;
}

export interface GraphChainData {
  nodes: GraphNode[];
  links: GraphLink[];
}
