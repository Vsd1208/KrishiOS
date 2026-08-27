import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAIConversation } from '../hooks/useAIConversation';
import { agentApi } from '@/services/api/agent';
import { weatherApi } from '@/services/api/weather';

vi.mock('@/services/api/agent', () => ({
  agentApi: {
    execute: vi.fn(),
  },
}));

vi.mock('@/services/api/weather', () => ({
  weatherApi: {
    getForecast: vi.fn(),
  },
}));

const mockAgentResponse = {
  goal: 'What is the fertilizer schedule for paddy?',
  status: 'completed' as const,
  execution_id: 'exec-99',
  results: [
    {
      agent: 'crop_advisory_agent',
      status: 'completed',
      output: 'Apply split nitrogen doses at basal and panicle initiation.',
      confidence: 0.94,
      grounded: true,
      citations: [
        {
          source_title: 'ICAR Paddy Nutrient Manual',
          authority: 'ICAR Research Complex',
          document_type: 'Bulletin',
          snippet: 'Split application optimizes nitrogen use efficiency.',
          confidence: 0.94,
        },
      ],
    },
  ],
};

describe('useAIConversation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(weatherApi.getForecast).mockResolvedValue({
      latitude: 17.247,
      longitude: 80.151,
      district: 'Khammam',
      state: 'Telangana',
      forecast_days: [],
      summary: 'Clear weather',
      spray_window_favorable: true,
      spray_window_reason: 'Favorable conditions',
    });
  });

  it('submits text query, updates messages stream, and stores AI response with citations', async () => {
    vi.mocked(agentApi.execute).mockResolvedValue(mockAgentResponse);

    const { result } = renderHook(() => useAIConversation());

    await act(async () => {
      await result.current.sendMessage({
        text: 'What is the fertilizer schedule for paddy?',
        language: 'en',
      });
    });

    expect(result.current.messages).toHaveLength(2);
    const userMsg = result.current.messages[0];
    expect(userMsg?.role).toBe('user');
    expect(userMsg?.userContent?.text).toBe(
      'What is the fertilizer schedule for paddy?'
    );

    const aiMsg = result.current.messages[1];
    expect(aiMsg?.role).toBe('assistant');
    expect(aiMsg?.aiContent?.text).toContain('Apply split nitrogen doses');
    expect(aiMsg?.aiContent?.confidence).toBe(0.94);
    expect(aiMsg?.aiContent?.citations).toHaveLength(1);
    expect(aiMsg?.aiContent?.citations?.[0]?.source_title).toBe('ICAR Paddy Nutrient Manual');
  });
});
