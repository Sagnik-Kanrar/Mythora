// Mythora PWA Service Worker
const CACHE_NAME = 'mythora-v1.0';

// Cache critical shell on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/manifest.json',
        '/favicon.svg',
        '/pwa-192x192.png',
        '/pwa-512x512.png'
      ]);
    })
  );
  self.skipWaiting();
});

// Clear older caches on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Network-first fetch strategy
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = event.request.url;

  // Never cache or intercept API endpoints, Firebase, Google APIs, or websockets
  if (
    url.includes('/api/') ||
    url.includes('firebase') ||
    url.includes('googleapis') ||
    url.includes('google') ||
    url.includes('identitytoolkit')
  ) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const cloned = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned));
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});
