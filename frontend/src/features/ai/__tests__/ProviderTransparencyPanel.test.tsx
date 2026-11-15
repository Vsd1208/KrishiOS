import '@/i18n';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProviderTransparencyPanel } from '../components/canvas/ProviderTransparencyPanel';
import { ProviderBadge } from '@/components/ai/ProviderBadge';
import * as providersApi from '@/services/api/providers';

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('ProviderBadge', () => {
  it('labels mocks explicitly and never as live', () => {
    const { container } = render(<ProviderBadge name="mock-stt-v1" version="0.1.0" kind="mock" />);
    expect(screen.getByText('mock-stt-v1')).toBeInTheDocument();
    expect(container.querySelector('[data-kind="mock"]')).not.toBeNull();
    expect(container.querySelector('[data-kind="live"]')).toBeNull();
  });

  it('shows not-configured when no provider', () => {
    render(<ProviderBadge name={null} kind={null} />);
    expect(screen.getByText(/Not configured/i)).toBeInTheDocument();
  });
});

describe('ProviderTransparencyPanel', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('lists every capability with its kind and off-device disclosure', async () => {
    vi.spyOn(providersApi, 'getProviders').mockResolvedValue({
      providers: [
        { capability: 'llm', configured: 'gemini', name: 'gemini', version: 'x', kind: 'live',
          sends_data_off_device: true, description: null, error: null },
        { capability: 'vision', configured: 'mock-v1', name: 'mock-v1', version: '0.1.0',
          kind: 'mock', sends_data_off_device: false, description: null, error: null },
      ],
      policy_violations: ['vision: mock provider not allowed'],
    });
    renderWithClient(<ProviderTransparencyPanel />);
    expect(await screen.findByText('vision')).toBeInTheDocument();
    expect(screen.getByText('llm')).toBeInTheDocument();
    expect(screen.getByText(/Sends data off device/i)).toBeInTheDocument();
    expect(screen.getByText(/vision: mock provider not allowed/)).toBeInTheDocument();
  });
});
