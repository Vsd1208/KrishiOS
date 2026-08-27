/**
 * KnowledgeGraphPage Component.
 *
 * Agronomic Knowledge Base & Knowledge Graph verification hub for Officers.
 * Allows reviewing GraphRAG entity candidates and running semantic retrieval
 * queries against official ICAR knowledge bases.
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { GraphCandidateCard } from '@/features/officer/components/GraphCandidateCard';
import { useGraphCandidates } from '@/features/officer/hooks/useOfficerData';
import { retrievalApi } from '@/services/api/retrieval';
import {
  Search,
  CheckCircle2,
  Award,
} from 'lucide-react';
import type { RetrievalSearchResponse } from '@/types/officer';

export const KnowledgeGraphPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'graph' | 'search'>('graph');
  const [candidateStatus, setCandidateStatus] = useState<'PENDING' | 'APPROVED' | 'REJECTED'>('PENDING');

  // Graph candidates query
  const { candidates, isLoading, reviewCandidate, isReviewing } = useGraphCandidates(candidateStatus);

  // Semantic search state
  const [searchQuery, setSearchQuery] = useState('Recommended fertilizer dose for paddy tillering');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<RetrievalSearchResponse | null>(null);

  const handleRunSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || isSearching) return;

    setIsSearching(true);
    try {
      const res = await retrievalApi.search({
        query: searchQuery.trim(),
        top_k: 5,
        score_threshold: 0.2,
      });
      setSearchResult(res);
    } catch (err) {
      console.error('Semantic search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">
            Knowledge Base &amp; Agronomic Graph
          </h1>
          <p className="text-body text-text-secondary">
            Validate GraphRAG entity extractions and search official ICAR agronomic literature
          </p>
        </div>

        {/* View Tabs */}
        <div className="flex p-1 rounded-xl bg-surface border border-border self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveTab('graph')}
            className={`px-4 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
              activeTab === 'graph'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-text-secondary hover:text-text'
            }`}
          >
            Graph Candidates ({candidates.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('search')}
            className={`px-4 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
              activeTab === 'search'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-text-secondary hover:text-text'
            }`}
          >
            Semantic Search Sandbox
          </button>
        </div>
      </div>

      {activeTab === 'graph' ? (
        <div className="space-y-4">
          {/* Status Filter */}
          <div className="flex gap-1.5 p-2 rounded-xl bg-surface border border-border">
            {(['PENDING', 'APPROVED', 'REJECTED'] as const).map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setCandidateStatus(st)}
                className={`px-3 py-1 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
                  candidateStatus === st
                    ? 'bg-primary-600 text-white shadow-sm'
                    : 'bg-surface-raised text-text-secondary hover:text-text'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Candidates List */}
          <div className="space-y-3">
            {isLoading ? (
              <div className="space-y-3">
                <Card variant="default" padding="md">
                  <Skeleton width="40%" height={24} />
                  <Skeleton height={50} className="mt-2" />
                </Card>
                <Card variant="default" padding="md">
                  <Skeleton width="40%" height={24} />
                  <Skeleton height={50} className="mt-2" />
                </Card>
              </div>
            ) : candidates.length === 0 ? (
              <Card variant="raised" padding="lg" className="text-center py-12">
                <CheckCircle2 className="w-8 h-8 text-success-600 mx-auto mb-2" aria-hidden="true" />
                <h3 className="text-subheading font-bold text-text">No {candidateStatus.toLowerCase()} candidates</h3>
                <p className="text-small text-text-secondary mt-1">
                  All extracted relationships in this category have been processed.
                </p>
              </Card>
            ) : (
              candidates.map((cand) => (
                <GraphCandidateCard
                  key={cand.id}
                  candidate={cand}
                  onReview={async (candidateId, payload) => {
                    await reviewCandidate({ candidateId, payload });
                  }}
                  isProcessing={isReviewing}
                />
              ))
            )}
          </div>
        </div>
      ) : (
        /* Semantic Search Sandbox */
        <div className="space-y-4">
          <form onSubmit={handleRunSearch} className="p-4 rounded-xl bg-surface border border-border space-y-3 shadow-sm">
            <label className="text-small font-bold text-text block">
              Search ICAR &amp; Agronomy Research Chunks:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. Stem borer chemical threshold and dosage in wetland paddy..."
                className="flex-1 px-3 py-2 rounded-lg bg-surface-raised border border-border text-small text-text focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <Button variant="primary" type="submit" disabled={isSearching}>
                <Search className="w-4 h-4 mr-1.5" aria-hidden="true" />
                {isSearching ? 'Searching...' : 'Search'}
              </Button>
            </div>
          </form>

          {/* Results List */}
          {searchResult && (
            <div className="space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between text-caption text-text-muted px-1">
                <span>
                  Found <strong>{searchResult.total_results}</strong> results ({searchResult.latency_ms.toFixed(1)} ms)
                </span>
                <span>Enterprise Semantic Index: krishios-live</span>
              </div>

              {searchResult.results.map((res, idx) => (
                <Card key={idx} variant="default" padding="md" className="space-y-2 border-l-4 border-l-primary-500">
                  <div className="flex items-center justify-between">
                    <span className="text-small font-bold text-text">
                      {res.citation?.title || 'ICAR Agricultural Advisory Guideline'}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full text-caption font-semibold bg-success-50 text-success-700">
                      Score: {Math.round(res.ranking_score * 100)}%
                    </span>
                  </div>

                  <p className="text-small text-text whitespace-pre-line leading-relaxed bg-surface-raised p-3 rounded-lg border border-border font-sans">
                    {res.chunk}
                  </p>

                  <div className="flex items-center gap-3 text-caption text-text-secondary pt-1">
                    <span className="flex items-center gap-1">
                      <Award className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                      {res.citation?.source || 'ICAR Research Complex'}
                    </span>
                    <span>•</span>
                    <span>Chunk ID: <code>{res.chunk_id.slice(0, 8)}</code></span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraphPage;
