/**
 * QueryErrorNotifier: one toast when data fails to load, so a page that does not handle its own
 * errors no longer just stays empty. Session expiry (401) is left to the auth flow, and a burst
 * of failures (for example when the server is down) produces a single toast.
 */

import React, { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { useToast } from './Toast';
import { ApiError } from '@/types/api';

const QUIET_MS = 15_000;

export const QueryErrorNotifier: React.FC = () => {
  const client = useQueryClient();
  const { showToast } = useToast();
  const { t } = useTranslation();
  const last = useRef(0);

  useEffect(
    () =>
      client.getQueryCache().subscribe((event) => {
        if (event.type !== 'updated' || event.action.type !== 'error') return;
        const err = event.action.error;
        if (err instanceof ApiError && err.status === 401) return;
        const now = Date.now();
        if (now - last.current < QUIET_MS) return;
        last.current = now;
        const offline = err instanceof ApiError ? err.status === 0 : typeof navigator !== 'undefined' && !navigator.onLine;
        showToast({
          variant: 'error',
          title: t('errorState.loadFailed.title'),
          message: offline ? t('errorState.offline.message') : t('errorState.loadFailed.message'),
        });
      }),
    [client, showToast, t],
  );

  return null;
};

export default QueryErrorNotifier;
