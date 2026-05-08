/**
 * awaClass Service Worker
 * Handles caching, offline fallback, and background sync
 */

const APP_VERSION   = 'v1';
const CACHE_STATIC  = `awaclass-static-${APP_VERSION}`;
const CACHE_PAGES   = `awaclass-pages-${APP_VERSION}`;
const CACHE_IMAGES  = `awaclass-images-${APP_VERSION}`;
const ALL_CACHES    = [CACHE_STATIC, CACHE_PAGES, CACHE_IMAGES];

// ─── Core shell assets (cache on install) ────────────────────────────────────
const STATIC_ASSETS = [
  '/',
  '/home',
  '/cbt/',
  '/cbt/mathematics/',
  '/cbt/physics/',
  '/cbt/physics/topics/',
  '/static/css/dashboard.css',
  '/static/images/slide1.png',
  '/static/images/slide2.png',
  '/static/images/slide3.png',
  '/static/images/slide4.png',
  // FontAwesome – cached at runtime; listed here so the SW knows about them
];

// ─── CDN hosts we cache at runtime ───────────────────────────────────────────
const CDN_HOSTS = [
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdnjs.cloudflare.com',
];

// ─── Routes that should NEVER be served from cache ──────────────────────────
const NETWORK_ONLY = [
  '/logout',
  '/post',
  '/cbt/submit/',
  '/chat/create/',
  '/chat/post/',          // comment / like sub-paths
  '/live/',
  '/follow/',
  '/like/',
  '/comment_like/',
  '/postcomment/',
];

// ─── Offline fallback page (inline HTML) ─────────────────────────────────────
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>awaClass — You're Offline</title>
  <style>
    :root{--ac-primary:#f97316;--ac-text:#1c1917;--ac-light:#fff7ed}
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Plus Jakarta Sans',-apple-system,sans-serif;
         background:var(--ac-light);color:var(--ac-text);
         display:flex;flex-direction:column;align-items:center;
         justify-content:center;min-height:100vh;text-align:center;padding:24px}
    .logo{width:64px;height:64px;background:var(--ac-primary);border-radius:16px;
          display:flex;align-items:center;justify-content:center;
          font-size:28px;font-weight:800;color:#fff;margin:0 auto 24px}
    h1{font-size:24px;font-weight:800;margin-bottom:10px}
    p{font-size:15px;color:#78716c;line-height:1.65;max-width:320px;margin:0 auto 28px}
    button{background:var(--ac-primary);color:#fff;border:none;
           padding:14px 32px;border-radius:12px;font-size:15px;
           font-weight:700;cursor:pointer}
    button:active{opacity:.85}
  </style>
</head>
<body>
  <div class="logo">A</div>
  <h1>You're offline</h1>
  <p>Check your internet connection and try again. Cached pages and questions are still available.</p>
  <button onclick="location.reload()">Try again</button>
</body>
</html>`;

// ═════════════════════════════════════════════════════════════════════════════
// INSTALL — pre-cache shell assets
// ═════════════════════════════════════════════════════════════════════════════
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_STATIC).then(async (cache) => {
      // Cache each asset individually so a single failure doesn't break install
      const results = await Promise.allSettled(
        STATIC_ASSETS.map((url) => cache.add(url).catch(() => null))
      );
      results.forEach((r, i) => {
        if (r.status === 'rejected') {
          console.warn('[SW] Failed to pre-cache:', STATIC_ASSETS[i]);
        }
      });
    })
  );
  self.skipWaiting();
});

// ═════════════════════════════════════════════════════════════════════════════
// ACTIVATE — clean up old caches and take control immediately
// ═════════════════════════════════════════════════════════════════════════════
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !ALL_CACHES.includes(k))
          .map((k) => {
            console.log('[SW] Deleting old cache:', k);
            return caches.delete(k);
          })
      )
    )
  );
  self.clients.claim();
});

// ═════════════════════════════════════════════════════════════════════════════
// FETCH — routing logic
// ═════════════════════════════════════════════════════════════════════════════
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignore non-GET, chrome-extension, and dev-server HMR requests
  if (request.method !== 'GET') return;
  if (!['http:', 'https:'].includes(url.protocol)) return;

  // ── 1. Network-only routes (mutations, auth, live) ───────────────────────
  if (NETWORK_ONLY.some((path) => url.pathname.startsWith(path))) {
    event.respondWith(networkOnly(request));
    return;
  }

  // ── 2. CDN assets (fonts, icons) – Cache-first ───────────────────────────
  if (CDN_HOSTS.includes(url.hostname)) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }

  // ── 3. Local static files – Cache-first ──────────────────────────────────
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }

  // ── 4. Images (any origin) – Cache-first ─────────────────────────────────
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, CACHE_IMAGES));
    return;
  }

  // ── 5. HTML navigation requests – Network-first with offline fallback ─────
  if (request.mode === 'navigate' || request.headers.get('Accept')?.includes('text/html')) {
    event.respondWith(networkFirstWithOfflineFallback(request));
    return;
  }

  // ── 6. Everything else – Stale-while-revalidate ──────────────────────────
  event.respondWith(staleWhileRevalidate(request, CACHE_STATIC));
});

// ═════════════════════════════════════════════════════════════════════════════
// CACHING STRATEGIES
// ═════════════════════════════════════════════════════════════════════════════

/** Always go to network; no cache fallback */
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response('Offline — this action requires a network connection.', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

/** Cache first → network fallback → null on failure */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 408, statusText: 'Offline' });
  }
}

/** Network first → cache fallback → inline offline page */
async function networkFirstWithOfflineFallback(request) {
  const cache = await caches.open(CACHE_PAGES);

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Try the root cached page as a generic fallback
    const rootCached = await caches.match('/');
    if (rootCached) return rootCached;

    return new Response(OFFLINE_HTML, {
      status: 503,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }
}

/** Serve from cache immediately; update cache in background */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const networkFetch = fetch(request).then((response) => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);

  return cached || (await networkFetch) || new Response('', { status: 408 });
}

// ═════════════════════════════════════════════════════════════════════════════
// MESSAGE — allow pages to skip waiting / clear caches on demand
// ═════════════════════════════════════════════════════════════════════════════
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();

  if (event.data === 'CLEAR_CACHE') {
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))));
  }
});
