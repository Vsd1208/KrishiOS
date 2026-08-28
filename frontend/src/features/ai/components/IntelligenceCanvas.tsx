/**
 * IntelligenceCanvas Component.
 *
 * Tabbed dual-pane inspection canvas providing deep insights into:
 * 1. GraphRAG reasoning chains (GraphChainVisualizer)
 * 2. Real-time telemetry & spray windows (TelemetryMatrix)
 * 3. Vision diagnostic lab (VisionDiagnosticLab)
 * 4. Grounding provenance & ICAR literature (ProvenanceExplorer)
 */

import React, { useState } from 'react';
import { GitFork, Activity, Eye, BookOpen, Layers } from 'lucide-react';
import { GraphChainVisualizer } from './canvas/GraphChainVisualizer';
import { TelemetryMatrix } from './canvas/TelemetryMatrix';
import { VisionDiagnosticLab } from './canvas/VisionDiagnosticLab';
import { ProvenanceExplorer } from './canvas/ProvenanceExplorer';
import type { CanvasTab } from '@/features/ai/types/workspace';
import type { AIMessageContent, ImageAttachment } from '@/features/ai/types/conversation';

interface IntelligenceCanvasProps {
  activeAIContent?: AIMessageContent;
  latestUserImage?: ImageAttachment;
  crop?: string;
  district?: string;
  className?: string;
}

export const IntelligenceCanvas: React.FC<IntelligenceCanvasProps> = ({
  activeAIContent,
  latestUserImage,
  crop = 'Paddy',
  district = 'Khammam',
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<CanvasTab>('graph');

  const tabs: { id: CanvasTab; label: string; icon: React.ReactNode }[] = [
    { id: 'graph', label: 'GraphRAG Chain', icon: <GitFork className="w-3.5 h-3.5" /> },
    { id: 'telemetry', label: 'Telemetry & Weather', icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'vision', label: 'Vision Lab', icon: <Eye className="w-3.5 h-3.5" /> },
    { id: 'provenance', label: 'Scientific Sources', icon: <BookOpen className="w-3.5 h-3.5" /> },
  ];

  return (
    <div
      aria-label="Intelligence Canvas"
      className={`flex flex-col h-full bg-surface border-l border-border rounded-2xl overflow-hidden shadow-sm ${className}`}
    >
      {/* Canvas Top Bar */}
      <div className="px-4 py-3 border-b border-border bg-surface-raised flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-primary-100 text-primary-700">
            <Layers className="w-4 h-4" />
          </div>
          <span className="text-small font-bold text-text">Decision Intelligence Canvas</span>
        </div>
        <span className="text-caption text-text-muted">
          Context: <strong>{crop}</strong> ({district})
        </span>
      </div>

      {/* Tabs Switcher */}
      <div className="px-3 pt-2 border-b border-border bg-surface flex items-center gap-1.5 overflow-x-auto shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-caption font-bold rounded-t-xl transition-all cursor-pointer flex items-center gap-1.5 shrink-0 border-b-2 ${
              activeTab === tab.id
                ? 'border-primary-600 text-primary-700 bg-primary-50/50'
                : 'border-transparent text-text-secondary hover:text-text hover:bg-surface-raised'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Canvas Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'graph' && (
          <GraphChainVisualizer
            graphPaths={activeAIContent?.evidence?.graph_paths}
            crop={crop}
          />
        )}

        {activeTab === 'telemetry' && (
          <TelemetryMatrix
            telemetry={activeAIContent?.evidence?.live_telemetry}
            district={district}
            crop={crop}
          />
        )}

        {activeTab === 'vision' && (
          <VisionDiagnosticLab
            image={latestUserImage}
            crop={crop}
          />
        )}

        {activeTab === 'provenance' && (
          <ProvenanceExplorer
            citations={activeAIContent?.citations}
            evaluation={activeAIContent?.evaluation}
          />
        )}
      </div>
    </div>
  );
};

export default IntelligenceCanvas;
