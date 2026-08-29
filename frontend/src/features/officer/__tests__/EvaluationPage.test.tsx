import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EvaluationPage } from '@/pages/officer/EvaluationPage';
import { alertsApi } from '@/services/api/alerts';
import { retrievalApi } from '@/services/api/retrieval';
import { reviewsApi } from '@/services/api/reviews';

vi.mock('@/services/api/alerts', () => ({
  alertsApi: {
    listDecisions: vi.fn(),
  },
}));

vi.mock('@/services/api/retrieval', () => ({
  retrievalApi: {
    getIndexStatus: vi.fn(),
  },
}));

vi.mock('@/services/api/reviews', () => ({
  reviewsApi: {
    listPendingReviews: vi.fn(),
  },
}));

describe('EvaluationPage (AI Trust & Observability Center)', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <EvaluationPage />
      </QueryClientProvider>
    );

  it('renders AI Trust Center header, Blue/Green index state, and decision inspection trace', async () => {
    vi.mocked(retrievalApi.getIndexStatus).mockResolvedValue({
      alias_name: 'krishios-live',
      active_collection: 'krishios_kb_v1',
      active_index: {
        id: 1,
        version_number: 1,
        collection_name: 'krishios_kb_v1',
        alias_name: 'krishios-live',
        index_kind: 'BASE',
        status: 'ACTIVE',
        build_mode: 'BLUE_GREEN',
        embedding_model: 'text-embedding-3-small',
        embedding_version: 'v1',
        vector_size: 384,
        chunk_count: 250,
        document_count: 12,
        created_at: '2026-08-28T10:00:00Z',
        updated_at: '2026-08-28T10:00:00Z',
      },
      previous_index: null,
      indexes: [],
    });

    vi.mocked(alertsApi.listDecisions).mockResolvedValue([
      {
        decision_id: '101',
        event_id: 'evt-1',
        farmer_id: 1,
        field_id: 1,
        risk_type: 'Yellow Stem Borer Outbreak',
        risk_severity: 'HIGH',
        confidence: 0.92,
        requires_review: true,
        advisory_text: 'Apply Cartap Hydrochloride 50 SP @ 2g/L as economic threshold is breached.',
        evidence_package: {
          citations: [
            {
              citation_id: 'cit-1',
              source_title: 'ICAR Rice Advisory Bulletin 2024',
              authority: 'ICAR NRRI',
              snippet: 'Recommended chemical control for stem borer in paddy tillering stage.',
              relevance_score: 0.94,
            },
          ],
          graph_paths: [
            {
              path: 'Paddy -> HAS_PEST -> Yellow Stem Borer -> CONTROLLED_BY -> Cartap Hydrochloride',
              confidence: 0.95,
            },
          ],
        },
        valid_until: '2026-08-30T10:00:00Z',
        created_at: '2026-08-28T10:30:00Z',
      },
    ]);

    vi.mocked(reviewsApi.listPendingReviews).mockResolvedValue([]);

    renderComponent();

    expect(screen.getByText(/AI Trust & Evaluation Center/i)).toBeInTheDocument();
    expect(screen.getByText(/Blue \/ Green Immutable Knowledge Index Health/i)).toBeInTheDocument();
    expect(await screen.findByText('Yellow Stem Borer Outbreak')).toBeInTheDocument();

    // Select decision to view trace
    const decisionCard = screen.getByText('Yellow Stem Borer Outbreak');
    fireEvent.click(decisionCard);

    expect(screen.getByText(/Decision Trace #101/i)).toBeInTheDocument();
    expect(screen.getByText('ICAR Rice Advisory Bulletin 2024')).toBeInTheDocument();
    expect(screen.getByText(/Paddy -> HAS_PEST -> Yellow Stem Borer/i)).toBeInTheDocument();
    expect(screen.getByText(/Telemetry & Instrumentation Notice:/i)).toBeInTheDocument();
  });
});
