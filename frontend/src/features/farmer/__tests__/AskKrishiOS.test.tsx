import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AskKrishiOS } from '../components/AskKrishiOS';
import { agentApi } from '@/services/api/agent';
import type { AgentExecutionResponse } from '@/types/agent';

vi.mock('@/services/api/agent', () => ({
  agentApi: {
    execute: vi.fn(),
  },
}));

const mockAgentResponse: AgentExecutionResponse = {
  goal: 'What is the best fertilizer dose for paddy?',
  status: 'completed',
  execution_id: 'exec-12345',
  results: [
    {
      agent: 'crop_advisory_agent',
      status: 'completed',
      output: 'Apply Urea in split doses: 50% at basal, 25% at tillering, and 25% at panicle initiation.',
      confidence: 0.92,
      grounded: true,
      citations: [
        {
          title: 'ICAR Paddy Nutrient Management Guide',
          authority: 'ICAR Research Complex',
          document_type: 'Agronomy Bulletin',
          snippet: 'Split application of nitrogen enhances fertilizer use efficiency in wetland paddy.',
        },
      ],
    },
  ],
};

describe('AskKrishiOS', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders quick suggestion prompts and input bar', () => {
    render(<AskKrishiOS />);

    expect(screen.getByText('Ask KrishiOS Intelligence')).toBeInTheDocument();
    expect(screen.getByText(/Suggested Questions:/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Ask in Telugu, Hindi, or English/i)
    ).toBeInTheDocument();
  });

  it('submits text query and displays AI advisory response with confidence and evidence', async () => {
    vi.mocked(agentApi.execute).mockResolvedValue(mockAgentResponse);

    render(<AskKrishiOS />);

    const input = screen.getByPlaceholderText(/Ask in Telugu, Hindi, or English/i);
    const sendButton = screen.getByRole('button', { name: /Ask/i });

    fireEvent.change(input, { target: { value: 'What is the best fertilizer dose for paddy?' } });
    fireEvent.click(sendButton);

    expect(agentApi.execute).toHaveBeenCalledWith(
      expect.objectContaining({
        goal: 'What is the best fertilizer dose for paddy?',
      })
    );

    // AI message should be rendered
    await waitFor(() => {
      expect(screen.getByText(/Apply Urea in split doses/i)).toBeInTheDocument();
      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText(/Why this answer\? \(1 agricultural sources\)/i)).toBeInTheDocument();
    });

    // Expand evidence drawer
    const evidenceToggle = screen.getByText(/Why this answer\?/i);
    fireEvent.click(evidenceToggle);

    expect(screen.getByText('ICAR Paddy Nutrient Management Guide')).toBeInTheDocument();
    expect(screen.getByText('ICAR Research Complex')).toBeInTheDocument();
  });
});
