/** Opt in to browser push notifications for official warnings (Phase 5). */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { BellRing } from 'lucide-react';

import { feedApi } from '@/services/api/govconnect';

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const pad = '='.repeat((4 - (base64url.length % 4)) % 4);
  const raw = atob((base64url + pad).replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

export const PushOptIn: React.FC = () => {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: ['push', 'config'], queryFn: feedApi.pushConfig });
  const [state, setState] = useState<'idle' | 'on' | 'denied' | 'error'>('idle');
  const supported =
    typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window;

  const enable = async (): Promise<void> => {
    try {
      if ((await Notification.requestPermission()) !== 'granted') {
        setState('denied');
        return;
      }
      const reg = await navigator.serviceWorker.register('/sw.js');
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: keyBytes(data?.public_key ?? ''),
      });
      await feedApi.subscribePush(sub.toJSON());
      setState('on');
    } catch {
      setState('error');
    }
  };

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 space-y-2">
      <h2 className="text-body font-bold text-text flex items-center gap-2">
        <BellRing className="w-4 h-4 text-primary-600" aria-hidden="true" />
        {t('push.title')}
      </h2>
      <p className="text-caption text-text-muted">{t('push.help')}</p>
      {!supported ? (
        <p className="text-caption text-text-muted">{t('push.unsupported')}</p>
      ) : !data?.enabled ? (
        <p className="text-caption text-text-muted">{t('push.notConfigured')}</p>
      ) : state === 'on' ? (
        <p className="text-caption text-success-700">{t('push.on')}</p>
      ) : (
        <button
          type="button"
          onClick={() => void enable()}
          className="px-4 py-2 rounded-lg bg-primary-600 text-white text-small font-semibold cursor-pointer"
        >
          {t('push.enable')}
        </button>
      )}
      {state === 'denied' && <p className="text-caption text-amber-800">{t('push.denied')}</p>}
      {state === 'error' && (
        <p role="alert" className="text-caption text-danger-700">
          {t('chat.error')}
        </p>
      )}
    </section>
  );
};
