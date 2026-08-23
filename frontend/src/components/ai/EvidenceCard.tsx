import React, { useState } from 'react';
import {
  Activity,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Cpu,
  Eye,
  GitFork,
  HelpCircle,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { EvidencePackage, GraphPath } from '@/types/proactive';
import { CitationCard } from '@/components/ai/CitationCard';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';
import { Badge } from '@/components/ui/Badge';

export interface EvidenceCardProps {
  /** The full AI evidence package */
  evidence: EvidencePackage;
  /** Additional CSS class names */
  className?: string;
  /** Whether sections start expanded by default */
  defaultExpanded?: boolean;
}

interface SectionHeaderProps {
  title: string;
  count?: number;
  isOpen: boolean;
  onToggle: () => void;
  icon: React.ReactNode;
  id: string;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  count,
  isOpen,
  onToggle,
  icon,
  id,
}) => (
  <button
    type="button"
    aria-expanded={isOpen}
    aria-controls={id}
    onClick={onToggle}
    className="flex w-full items-center justify-between py-2.5 px-3 text-left font-medium text-text hover:bg-surface-raised transition-colors rounded-md focus-visible:ring-2 focus-visible:ring-primary-500"
  >
    <div className="flex items-center gap-2 text-sm">
      <span className="text-primary-600">{icon}</span>
      <span className="font-semibold">{title}</span>
      {count !== undefined && count > 0 && (
        <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold rounded-full bg-primary-50 text-primary-700 border border-primary-200">
          {count}
        </span>
      )}
    </div>
    <span className="text-text-muted">
      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
    </span>
  </button>
);

/**
 * Format primitive telemetry values into friendly human-readable strings.
 */
const formatTelemetryValue = (value: unknown): string => {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2);
  }
  if (typeof value === 'boolean') {
    return value ? 'True' : 'False';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
};

/**
 * Convert camelCase or snake_case key to Title Case.
 */
const formatKey = (key: string): string => {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

/**
 * EvidenceCard decomposes and visualizes the complete evidence package behind AI recommendations.
 * Includes live sensor telemetry, statutory citations, knowledge graph paths, rules, and vision findings.
 */
export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  evidence,
  className = '',
  defaultExpanded = true,
}) => {
  const {
    live_telemetry,
    citations,
    graph_paths,
    vision_findings,
    active_rules,
    freshness_seconds,
    confidence_breakdown,
  } = evidence;

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    breakdown: defaultExpanded,
    telemetry: defaultExpanded,
    citations: defaultExpanded,
    graphs: defaultExpanded,
    rules: defaultExpanded,
    vision: defaultExpanded,
  });

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const telemetryKeys = live_telemetry ? Object.keys(live_telemetry) : [];
  const hasTelemetry = telemetryKeys.length > 0;
  const hasCitations = citations && citations.length > 0;
  const hasGraphs = graph_paths && graph_paths.length > 0;
  const hasRules = active_rules && active_rules.length > 0;
  const hasVision = vision_findings && vision_findings.length > 0;
  const breakdownEntries = confidence_breakdown ? Object.entries(confidence_breakdown) : [];
  const hasBreakdown = breakdownEntries.length > 0;

  const isCompletelyEmpty =
    !hasTelemetry && !hasCitations && !hasGraphs && !hasRules && !hasVision && !hasBreakdown;

  return (
    <section
      aria-label="AI Evidence Package"
      className={`rounded-lg border border-border bg-surface p-4 shadow-card ${className}`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <div className="rounded-md bg-primary-50 p-1.5 text-primary-700">
            <Layers className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text">Evidence Package</h3>
            <p className="text-xs text-text-secondary">
              Verifiable facts, telemetry, and rules supporting this decision
            </p>
          </div>
        </div>

        {freshness_seconds !== undefined && (
          <FreshnessIndicator freshnessSeconds={freshness_seconds} size="sm" />
        )}
      </div>

      {isCompletelyEmpty ? (
        <div className="py-8 text-center text-xs text-text-muted">
          <HelpCircle className="mx-auto mb-2 w-6 h-6 text-text-muted opacity-60" aria-hidden="true" />
          <p>No telemetry or citations attached to this decision.</p>
        </div>
      ) : (
        <div className="divide-y divide-border/60">
          {/* Confidence Breakdown */}
          {hasBreakdown && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-breakdown-section"
                title="Confidence Breakdown"
                icon={<Sparkles className="w-4 h-4" />}
                isOpen={Boolean(openSections.breakdown)}
                onToggle={() => toggleSection('breakdown')}
              />
              {openSections.breakdown && (
                <div id="evidence-breakdown-section" className="mt-2 space-y-2.5 px-3">
                  {breakdownEntries.map(([source, score]) => {
                    const normalized = score > 1 ? score / 100 : Math.max(0, Math.min(1, score));
                    const percentage = Math.round(normalized * 100);
                    const colorClass =
                      normalized >= 0.8
                        ? 'bg-success-500'
                        : normalized >= 0.5
                        ? 'bg-warning-500'
                        : 'bg-danger-500';

                    return (
                      <div key={source} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium text-text">
                          <span className="text-text-secondary">{formatKey(source)}</span>
                          <span className="font-semibold tabular-nums">{percentage}%</span>
                        </div>
                        <div
                          className="h-2 w-full overflow-hidden rounded-full bg-surface-raised border border-border/80"
                          role="progressbar"
                          aria-valuenow={percentage}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-label={`${formatKey(source)} confidence ${percentage}%`}
                        >
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${colorClass}`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Live Telemetry */}
          {hasTelemetry && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-telemetry-section"
                title="Live Field Telemetry"
                count={telemetryKeys.length}
                icon={<Activity className="w-4 h-4" />}
                isOpen={Boolean(openSections.telemetry)}
                onToggle={() => toggleSection('telemetry')}
              />
              {openSections.telemetry && (
                <div
                  id="evidence-telemetry-section"
                  className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 px-3"
                >
                  {telemetryKeys.map((key) => {
                    const val = live_telemetry?.[key];
                    return (
                      <div
                        key={key}
                        className="rounded-md border border-border bg-surface-raised p-2.5 text-xs transition-colors hover:border-primary-200"
                      >
                        <span className="block text-text-muted font-medium truncate" title={key}>
                          {formatKey(key)}
                        </span>
                        <span className="mt-0.5 block font-semibold text-text tabular-nums break-words">
                          {formatTelemetryValue(val)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Statutory & Research Citations */}
          {hasCitations && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-citations-section"
                title="Scientific & Advisory Citations"
                count={citations.length}
                icon={<BookOpen className="w-4 h-4" />}
                isOpen={Boolean(openSections.citations)}
                onToggle={() => toggleSection('citations')}
              />
              {openSections.citations && (
                <div id="evidence-citations-section" className="mt-2 space-y-2 px-3">
                  {citations.map((citation, index) => (
                    <CitationCard
                      key={citation.citation_id || `citation-${index}`}
                      citation={citation}
                      index={index + 1}
                      compact
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Knowledge Graph Paths */}
          {hasGraphs && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-graphs-section"
                title="Agronomic Graph Paths"
                count={graph_paths.length}
                icon={<GitFork className="w-4 h-4" />}
                isOpen={Boolean(openSections.graphs)}
                onToggle={() => toggleSection('graphs')}
              />
              {openSections.graphs && (
                <div id="evidence-graphs-section" className="mt-2 space-y-2 px-3">
                  {graph_paths.map((gp: GraphPath, idx: number) => {
                    const confPercent =
                      gp.confidence !== undefined ? Math.round(gp.confidence * 100) : null;
                    return (
                      <div
                        key={`gp-${idx}`}
                        className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface-raised p-2.5 text-xs text-text"
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span className="font-medium text-text break-words font-mono text-[11px]">
                            {gp.path}
                          </span>
                          {gp.relationship && (
                            <span className="shrink-0 rounded bg-primary-100 px-1.5 py-0.5 text-[10px] font-semibold text-primary-800">
                              {gp.relationship}
                            </span>
                          )}
                        </div>
                        {confPercent !== null && (
                          <span className="shrink-0 font-medium tabular-nums text-text-secondary">
                            {confPercent}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Active Rules */}
          {hasRules && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-rules-section"
                title="Triggered Expert Rules"
                count={active_rules.length}
                icon={<Cpu className="w-4 h-4" />}
                isOpen={Boolean(openSections.rules)}
                onToggle={() => toggleSection('rules')}
              />
              {openSections.rules && (
                <div id="evidence-rules-section" className="mt-2 flex flex-wrap gap-1.5 px-3">
                  {active_rules.map((rule, idx) => (
                    <Badge
                      key={`rule-${idx}`}
                      variant="primary"
                      size="sm"
                      className="font-mono text-[11px]"
                    >
                      {rule}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Vision Findings */}
          {hasVision && (
            <div className="py-2.5">
              <SectionHeader
                id="evidence-vision-section"
                title="Vision & Imagery Findings"
                count={vision_findings.length}
                icon={<Eye className="w-4 h-4" />}
                isOpen={Boolean(openSections.vision)}
                onToggle={() => toggleSection('vision')}
              />
              {openSections.vision && (
                <div id="evidence-vision-section" className="mt-2 space-y-2 px-3">
                  {vision_findings.map((finding, idx) => (
                    <div
                      key={`vf-${idx}`}
                      className="rounded-md border border-border bg-surface-raised p-2 text-xs font-mono"
                    >
                      <pre className="whitespace-pre-wrap break-words text-text-secondary">
                        {JSON.stringify(finding, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default EvidenceCard;
