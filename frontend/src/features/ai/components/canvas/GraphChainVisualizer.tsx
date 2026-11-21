/**
 * GraphChainVisualizer: the knowledge-graph paths the backend used for this answer
 * (entity -> RELATIONSHIP -> entity). When none were used it says so; it never invents a chain.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { GitFork, ArrowRight } from 'lucide-react';
import type { GraphPath } from '@/types/proactive';

interface GraphChainVisualizerProps {
  graphPaths?: GraphPath[];
  crop?: string;
}

const isRelationship = (part: string) => part.toUpperCase() === part && part.includes('_');

export const GraphChainVisualizer: React.FC<GraphChainVisualizerProps> = ({ graphPaths = [] }) => {
  const { t } = useTranslation();

  return (
    <div className="space-y-4 animate-fadeIn">
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-purple-100 text-purple-700">
          <GitFork className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-small font-bold text-text">{t('canvas.graph.title')}</h4>
          <p className="text-caption text-text-muted">{t('canvas.graph.subtitle')}</p>
        </div>
      </div>

      {graphPaths.length === 0 ? (
        <div
          className="p-6 rounded-xl border border-dashed border-border bg-surface-raised text-center space-y-2"
          data-testid="no-graph"
        >
          <GitFork className="w-8 h-8 text-text-muted mx-auto opacity-60" aria-hidden="true" />
          <p className="text-small text-text-secondary font-medium">{t('canvas.graph.none')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {graphPaths.map((chain, cIdx) => (
            <div key={cIdx} className="p-3.5 rounded-xl bg-surface border border-border space-y-3 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
                <span className="text-caption font-bold text-text-secondary uppercase">
                  {t('canvas.graph.chain', { n: cIdx + 1 })}
                </span>
                <div className="flex items-center gap-2">
                  {typeof chain.confidence === 'number' && (
                    <span className="text-caption font-semibold text-text-secondary">
                      {t('canvas.graph.confidence', { pct: Math.round(chain.confidence * 100) })}
                    </span>
                  )}
                  {chain.relationship && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary-50 text-primary-700 border border-primary-200">
                      {chain.relationship.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-caption">
                {chain.path.split(' -> ').map((part, pIdx) =>
                  isRelationship(part) ? (
                    <span
                      key={pIdx}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold text-primary-700 bg-primary-50 border border-primary-200 uppercase"
                    >
                      <span>{part.replace(/_/g, ' ')}</span>
                      <ArrowRight className="w-2.5 h-2.5" aria-hidden="true" />
                    </span>
                  ) : (
                    <span
                      key={pIdx}
                      className="px-2.5 py-1 rounded-lg font-medium border text-xs bg-surface-raised text-text border-border break-words"
                    >
                      {part}
                    </span>
                  ),
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GraphChainVisualizer;
