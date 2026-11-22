/** A crashing page shows a recoverable screen inside the shell; failed loads raise one toast. */

import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router-dom';

import i18n from '@/i18n';
import { RouteError, isChunkLoadError } from '../RouteError';
import { QueryErrorNotifier } from '../QueryErrorNotifier';
import { ToastProvider } from '../Toast';
import { ApiError } from '@/types/api';

beforeEach(async () => {
  await i18n.changeLanguage('en');
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

const Boom: React.FC = () => {
  throw new Error('render failed');
};

describe('RouteError', () => {
  it('keeps the shell and shows a reload screen when a page crashes', () => {
    const router = createMemoryRouter(
      [
        {
          path: '/',
          element: (
            <div>
              <nav>Menu</nav>
              <Outlet />
            </div>
          ),
          errorElement: <RouteError fullPage />,
          children: [{ index: true, element: <Boom />, errorElement: <RouteError /> }],
        },
      ],
      { initialEntries: ['/'] },
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByText('Menu')).toBeInTheDocument();
    expect(screen.getByText('This page could not be shown')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/render failed/);
  });

  it('recognises a failed page download', () => {
    expect(isChunkLoadError(new TypeError('Failed to fetch dynamically imported module: /x.js'))).toBe(true);
    expect(isChunkLoadError(new Error('render failed'))).toBe(false);
  });
});

describe('QueryErrorNotifier', () => {
  it('shows one toast for a burst of failures and none for an expired session', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <QueryErrorNotifier />
        </ToastProvider>
      </QueryClientProvider>,
    );
    await act(async () => {
      await client.fetchQuery({ queryKey: ['a'], queryFn: () => Promise.reject(new ApiError(401, 'x', 'x')) }).catch(() => {});
    });
    expect(screen.queryByText('Some information could not be loaded')).not.toBeInTheDocument();

    await act(async () => {
      for (const k of ['b', 'c']) {
        await client.fetchQuery({ queryKey: [k], queryFn: () => Promise.reject(new ApiError(500, 'x', 'x')) }).catch(() => {});
      }
    });
    expect(screen.getAllByText('Some information could not be loaded')).toHaveLength(1);
  });
});
