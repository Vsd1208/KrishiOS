import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';

import i18n from '@/i18n';

// Every test renders with real English strings, never raw translation keys; a test that needs
// Hindi or Telugu switches language itself.
beforeEach(async () => {
  await i18n.changeLanguage('en');
});

afterEach(() => {
  cleanup();
});
