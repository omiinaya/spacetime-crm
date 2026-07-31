/**
 * SpacetimeCRM Service Worker
 * Handles push notifications and provides offline caching for the PWA.
 */
const CACHE_NAME = 'spacetime-crm-v1';

// Install event — pre-cache critical assets
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/manifest.json',
      ]).catch(() => {
        // Non-critical — service worker still works without pre-cache
      });
    })
  );
});

// Activate event — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  return self.clients.claim();
});

// Push event — show notification
self.addEventListener('push', (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.body || '',
      icon: data.icon || '/favicon.ico',
      badge: '/favicon.ico',
      data: {
        url: data.url || '/',
      },
      vibrate: [200, 100, 200],
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'SpacetimeCRM', options)
    );
  } catch (e) {
    // Non-JSON payload — show raw text
    event.waitUntil(
      self.registration.showNotification(event.data.text(), {
        icon: '/favicon.ico',
      })
    );
  }
});

// Notification click — open the app
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Focus existing window if open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            return client.focus().then((focused) => {
              if (focused && 'navigate' in focused && urlToOpen !== '/') {
                focused.navigate(urlToOpen);
              }
              return focused;
            });
          }
        }
        // Otherwise open a new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Fetch — offline support: NetworkFirst for API reads and pages, cache-first
// for static assets. Writes are passed through untouched (never cached).
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const isAPI = url.pathname.startsWith('/api/');
  const isPage = request.mode === 'navigate';

  // API + page navigations: try network, fall back to cache when offline.
  if (isAPI || isPage) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match('/index.html')),
        ),
    );
    return;
  }

  // Static assets: cache-first with network refresh.
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        }),
    ),
  );
});
