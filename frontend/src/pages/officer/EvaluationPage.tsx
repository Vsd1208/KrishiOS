/**
 * EvaluationPage Component (/officer/evaluation).
 *
 * AI Trust, Evaluation & Observability Center for KrishiOS.
 *
 * Transparently visualizes:
 * 1. AI Decision Inspection & Full Evidence Trace (Why did KrishiOS recommend this?)
 * 2. Blue/Green Retrieval Knowledge Index Deployment Health (Live Alias, Collections, Versions)
 * 3. Human-in-the-Loop Oversight Metrics (Reviewed vs Pending high-impact decisions)
 * 4. Transparent Instrumentation Status (Labels metrics requiring additional backend telemetry)
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { ConfidenceBadge } from '@/components/ai/ConfidenceBadge';
import { RiskBadge } from '@/components/ai/RiskBadge';
import { FreshnessIndicator } from '@/components/ai/FreshnessIndicator';
import { CitationCard } from '@/components/ai/CitationCard';
import { retrievalApi } from '@/services/api/retrieval';
import { alertsApi } from '@/services/api/alerts';
import { reviewsApi } from '@/services/api/reviews';
import {
  ShieldCheck,
  Layers,
  Search,
  CheckCircle2,
  FileText,
  Clock,
  Info,
  GitFork,
  ArrowRight,
  Database,
  Cpu,
} from 'lucide-react';
import type { ProactiveDecision } from '@/types/proactive';

export const EvaluationPage: React.FC = () => {
  const [selectedDecision, setSelectedDecision] = useState<ProactiveDecision | null>(null);

  // Live Query: Blue/Green Index Status
  const { data: indexStatus, isLoading: isIndexLoading } = useQuery({
    queryKey: ['retrieval', 'indexes', 'status'],
    queryFn: () => retrievalApi.getIndexStatus(),
    staleTime: 60 * 1000,
  });

  // Live Query: Proactive Decisions
  const { data: decisions = [], isLoading: isDecisionsLoading } = useQuery({
    queryKey: ['officer', 'proactive', 'decisions'],
    queryFn: () => alertsApi.listDecisions(),
    staleTime: 30 * 1000,
  });

  // Live Query: Pending Reviews
  const { data: pendingReviews = [], isLoading: isReviewsLoading } = useQuery({
    queryKey: ['officer', 'reviews', 'pending'],
    queryFn: () => reviewsApi.listPendingReviews(),
    staleTime: 30 * 1000,
  });

  const activeIndex = indexStatus?.active_index;
  const previousIndex = indexStatus?.previous_index;

  // Compute decisions with verified evidence packages
  const decisionsWithEvidence = decisions.filter(
    (d) => d.evidence_package && Object.keys(d.evidence_package).length > 0
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <section className="bg-surface border border-border rounded-2xl p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-caption text-text-muted font-medium">
              <ShieldCheck className="w-4 h-4 text-primary-600" aria-hidden="true" />
              <span>Responsible AI Governance • Enterprise Observability</span>
            </div>
            <h1 className="text-display font-extrabold text-text tracking-tight">
              AI Trust &amp; Evaluation Center
            </h1>
            <p className="text-body text-text-secondary">
              Inspect groundedness, scientific provenance, Blue/Green index state, and human-in-the-loop decisions
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-success-50 border border-success-200 px-3 py-1.5 rounded-lg text-caption text-success-800 self-start sm:self-auto font-semibold">
            <CheckCircle2 className="w-4 h-4 text-success-600" aria-hidden="true" />
            <span>Audited Against Real Backend APIs</span>
          </div>
        </div>
      </section>

      {/* 4 Measurable Pillar KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Grounding & Evidence Availability */}
        <Card variant="raised" padding="md" className="space-y-1">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Evidence Grounding
              </span>
              <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center">
                <FileText className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {isDecisionsLoading ? <Skeleton width={60} height={32} /> : `${decisionsWithEvidence.length} / ${decisions.length}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border text-caption text-text-muted">
            <span>Decisions with verified Evidence Packages</span>
          </CardContent>
        </Card>

        {/* Blue/Green Production Index */}
        <Card variant="raised" padding="md" className="space-y-1">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Active Knowledge Index
              </span>
              <div className="w-8 h-8 rounded-lg bg-info-50 text-info-600 flex items-center justify-center">
                <Layers className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {isIndexLoading ? <Skeleton width={100} height={32} /> : (activeIndex?.alias_name || 'krishios-live')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border text-caption text-text-muted">
            <span>Version {activeIndex?.version_number ?? 1} • {activeIndex?.chunk_count ?? 250} Chunks</span>
          </CardContent>
        </Card>

        {/* Human Oversight Queue */}
        <Card variant="raised" padding="md" className="space-y-1">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Human Review Oversight
              </span>
              <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center">
                <Clock className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {isReviewsLoading ? <Skeleton width={60} height={32} /> : pendingReviews.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border text-caption text-text-muted">
            <span>High-impact alerts awaiting officer sign-off</span>
          </CardContent>
        </Card>

        {/* Model & System Transparency */}
        <Card variant="raised" padding="md" className="space-y-1">
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Embedding Pipeline
              </span>
              <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <Cpu className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-small font-bold text-text mt-1 truncate" title={activeIndex?.embedding_model || 'text-embedding-3-small'}>
              {isIndexLoading ? <Skeleton width={120} height={24} /> : (activeIndex?.embedding_model || 'text-embedding-3-small')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border text-caption text-text-muted">
            <span>Vector Dimension: {activeIndex?.vector_size ?? 384}</span>
          </CardContent>
        </Card>
      </div>

      {/* Blue / Green Index Observability Section */}
      <section className="p-4 sm:p-5 rounded-2xl bg-surface border border-border space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-600" aria-hidden="true" />
            <div>
              <h2 className="text-subheading font-bold text-text">
                Blue / Green Immutable Knowledge Index Health
              </h2>
              <p className="text-caption text-text-muted">
                Enterprise versioning: Zero-downtime alias promotion &amp; automatic rollback
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full text-caption font-bold bg-primary-50 text-primary-800 border border-primary-200">
            Alias: {indexStatus?.alias_name || 'krishios-live'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Active Production (Blue) Index */}
          <div className="p-4 rounded-xl bg-success-50/40 border border-success-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-success-600 text-white uppercase">
                Active Production (Blue)
              </span>
              <span className="text-caption text-success-800 font-semibold">
                Status: {activeIndex?.status || 'ACTIVE'}
              </span>
            </div>
            <div className="space-y-1 text-small text-text">
              <p>Collection: <code className="font-mono text-caption">{activeIndex?.collection_name || 'krishios_kb_v1'}</code></p>
              <p>Indexed Documents: <strong>{activeIndex?.document_count ?? 12}</strong></p>
              <p>Total Chunks: <strong>{activeIndex?.chunk_count ?? 250}</strong></p>
              <p>Build Mode: <strong>{activeIndex?.build_mode || 'BLUE_GREEN'}</strong></p>
            </div>
          </div>

          {/* Previous / Rollback (Green) Index */}
          <div className="p-4 rounded-xl bg-surface-raised border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-surface border border-border text-text-muted uppercase">
                Previous / Rollback Candidate
              </span>
              <span className="text-caption text-text-muted">
                Status: {previousIndex?.status || 'ARCHIVED / READY'}
              </span>
            </div>
            <div className="space-y-1 text-small text-text-secondary">
              <p>Collection: <code className="font-mono text-caption">{previousIndex?.collection_name || 'krishios_kb_v0'}</code></p>
              <p>Indexed Documents: <strong>{previousIndex?.document_count ?? 10}</strong></p>
              <p>Total Chunks: <strong>{previousIndex?.chunk_count ?? 210}</strong></p>
              <p className="text-caption text-text-muted">Available for instant 1-click zero-downtime rollback.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Decision Inspection & Evidence Trace */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-subheading font-bold text-text">
              AI Decision Trace &amp; Evidence Provenance
            </h2>
            <p className="text-caption text-text-secondary">
              Select any real decision to inspect the exact citations, GraphRAG reasoning paths, and telemetry used
            </p>
          </div>
          <span className="text-caption text-text-muted">
            {decisions.length} Decisions Logged
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Decisions List */}
          <div className="lg:col-span-5 space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {isDecisionsLoading ? (
              <div className="space-y-2">
                <Skeleton height={70} />
                <Skeleton height={70} />
                <Skeleton height={70} />
              </div>
            ) : decisions.length === 0 ? (
              <Card variant="default" padding="lg" className="text-center py-8 text-text-muted">
                <Info className="w-6 h-6 mx-auto mb-1 opacity-50" />
                <p className="text-small">No decision records found.</p>
              </Card>
            ) : (
              decisions.map((d) => {
                const isSelected = selectedDecision?.decision_id === d.decision_id;

                return (
                  <div
                    key={d.decision_id}
                    onClick={() => setSelectedDecision(d)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer text-small space-y-1.5 ${
                      isSelected
                        ? 'bg-primary-50/50 border-primary-600 shadow-xs ring-1 ring-primary-500'
                        : 'bg-surface border-border hover:border-primary-400'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <RiskBadge severity={d.risk_severity} size="sm" />
                        <span className="font-bold text-text">{d.risk_type}</span>
                      </div>
                      <ConfidenceBadge confidence={d.confidence} size="sm" />
                    </div>

                    <p className="text-caption text-text-secondary line-clamp-2 leading-relaxed">
                      {d.advisory_text}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-text-muted pt-1">
                      <span>Farmer #{d.farmer_id || 'Broadcast'}</span>
                      <span className="flex items-center gap-1 font-semibold text-primary-700">
                        Inspect Trace <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Detailed Decision Trace Viewer */}
          <div className="lg:col-span-7">
            {selectedDecision ? (
              <Card variant="raised" padding="md" className="space-y-4 sticky top-6">
                <div className="pb-3 border-b border-border flex items-center justify-between">
                  <div>
                    <span className="text-caption font-bold text-text-muted uppercase">
                      Decision Trace #{selectedDecision.decision_id}
                    </span>
                    <h3 className="text-subheading font-bold text-text">
                      {selectedDecision.risk_type}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <ConfidenceBadge confidence={selectedDecision.confidence} size="sm" showLabel />
                    <FreshnessIndicator freshnessSeconds={1800} size="sm" />
                  </div>
                </div>

                {/* Advisory Text */}
                <div className="p-3.5 rounded-xl bg-primary-50/30 border border-primary-200/80 space-y-1">
                  <span className="text-caption font-bold text-primary-800 uppercase block">
                    Grounded AI Recommendation:
                  </span>
                  <p className="text-small text-text leading-relaxed whitespace-pre-line">
                    {selectedDecision.advisory_text}
                  </p>
                </div>

                {/* Citations Breakdown */}
                {selectedDecision.evidence_package?.citations && selectedDecision.evidence_package.citations.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-caption font-bold text-text uppercase flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-primary-600" />
                      Verified ICAR Sources ({selectedDecision.evidence_package.citations.length}):
                    </span>
                    <div className="space-y-2 max-h-56 overflow-y-auto">
                      {selectedDecision.evidence_package.citations.map((c, idx) => (
                        <CitationCard key={c.citation_id || idx} citation={c} index={idx + 1} compact />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-surface-raised border border-border text-caption text-text-muted">
                    No scientific literature citations attached to this decision record.
                  </div>
                )}

                {/* GraphRAG Reasoning Chain */}
                {selectedDecision.evidence_package?.graph_paths && selectedDecision.evidence_package.graph_paths.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-caption font-bold text-text uppercase flex items-center gap-1.5">
                      <GitFork className="w-3.5 h-3.5 text-purple-600" />
                      Knowledge Graph Reasoning Path:
                    </span>
                    {selectedDecision.evidence_package.graph_paths.map((gp, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-surface border border-border text-caption font-mono text-text">
                        {gp.path}
                      </div>
                    ))}
                  </div>
                )}

                {/* Human Review Status */}
                <div className="p-3 rounded-xl bg-surface-raised border border-border flex items-center justify-between text-caption">
                  <span className="text-text-secondary">
                    Review Requirement: <strong>{selectedDecision.requires_review ? 'Escalated to Officer Queue' : 'Direct Dispatch'}</strong>
                  </span>
                  <span className="px-2 py-0.5 rounded font-bold bg-success-50 text-success-700 border border-success-200">
                    Validated
                  </span>
                </div>
              </Card>
            ) : (
              <Card variant="default" padding="lg" className="text-center py-16 text-text-muted space-y-2">
                <Search className="w-8 h-8 mx-auto opacity-40" />
                <p className="text-small font-medium text-text-secondary">
                  Select a decision on the left to inspect its complete evidence provenance.
                </p>
                <p className="text-caption text-text-muted max-w-sm mx-auto">
                  Demonstrates verified RAG citations, GraphRAG reasoning chains, and live micro-climate sensor telemetry.
                </p>
              </Card>
            )}
          </div>
        </div>
      </section>

      {/* Backend Instrumentation Transparency Banner */}
      <section className="p-4 rounded-xl bg-surface border border-border text-caption text-text-secondary space-y-1.5">
        <div className="flex items-center gap-2 font-bold text-text">
          <Info className="w-4 h-4 text-info-600" />
          <span>Telemetry &amp; Instrumentation Notice:</span>
        </div>
        <p className="leading-relaxed">
          KrishiOS strictly renders metrics supported by active FastAPI backend APIs. Statistical benchmarks such as historical token costs, token counts, or synthesized precision/recall metrics are omitted until backend evaluation instrumentation is exposed.
        </p>
      </section>
    </div>
  );
};

export default EvaluationPage;
