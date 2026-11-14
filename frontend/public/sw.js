/* KrishiOS service worker (Phase 5, F3): offline reading + push notifications.
 *
 * - App shell (HTML/JS/CSS) is cached on first load and served cache-first.
 * - A short allow-list of read-only API GETs (weather feed, Govt Updates inbox, crop list) is
 *   network-first with a cached fallback, so the latest values stay readable offline. The
 *   response is marked with `x-krishios-offline: 1` so the UI can say it is not fresh.
 * - Nothing else (POSTs, personal endpoints outside the list) is cached.
 */
const SHELL = 'krishios-shell-v1';
const DATA = 'krishios-data-v1';
const OFFLINE_GET = [
  '/api/v1/govconnect/weather-feed',
  '/api/v1/govconnect/inbox',
  '/api/v1/catalog/crops',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(['/', '/manifest.webmanifest'])));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

async function networkFirst(request) {
  const cache = await caches.open(DATA);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (!cached) throw err;
    const headers = new Headers(cached.headers);
    headers.set('x-krishios-offline', '1');
    return new Response(await cached.blob(), { status: 200, headers });
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL);
  const cached = await cache.match(request);
  if (cached) {
    fetch(request).then((r) => r.ok && cache.put(request, r.clone())).catch(() => {});
    return cached;
  }
  const response = await fetch(request);
  if (response.ok && request.method === 'GET') await cache.put(request, response.clone());
  return response;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) {
    if (OFFLINE_GET.some((p) => url.pathname.startsWith(p))) {
      event.respondWith(networkFirst(request));
    }
    return;
  }
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/')));
    return;
  }
  event.respondWith(cacheFirst(request));
});

self.addEventListener('push', (event) => {
  let data = { title: 'KrishiOS', body: '', url: '/farmer/updates' };
  try {
    data = { ...data, ...event.data.json() };
  } catch (e) {
    /* plain text payload */
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body, tag: data.tag, lang: data.lang, data: { url: data.url },
      icon: '/favicon.svg',
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/farmer/updates';
  event.waitUntil(self.clients.openWindow(url));
});
