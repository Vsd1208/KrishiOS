/**
 * RouteError: shown in place of a page that crashed while rendering or failed to load its code,
 * so the app shell and menu stay usable instead of the whole screen going blank.
 */

import React from 'react';
import { isRouteErrorResponse, useRouteError } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { ErrorState } from './ErrorState';

/** True when the browser could not download a page's code, usually after a new version was deployed. */
export function isChunkLoadError(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  return /dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk/i.test(text);
}

export const RouteError: React.FC<{ fullPage?: boolean }> = ({ fullPage = false }) => {
  const error = useRouteError();
  const { t } = useTranslation();

  if (isRouteErrorResponse(error)) {
    return <ErrorState statusCode={error.status} fullPage={fullPage} onRetry={() => window.location.reload()} />;
  }
  if (import.meta.env.DEV) {
    console.error('Page crashed:', error);
  }
  return (
    <ErrorState
      title={isChunkLoadError(error) ? t('errorState.update.title') : t('errorState.crash.title')}
      message={isChunkLoadError(error) ? t('errorState.update.message') : t('errorState.crash.message')}
      retryLabel={t('errorState.reload')}
      onRetry={() => window.location.reload()}
      fullPage={fullPage}
    />
  );
};

export default RouteError;
