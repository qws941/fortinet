// Service Worker for FortiGate Nextrade PWA
const CACHE_NAME = 'fortigate-nextrade-v1';
const DYNAMIC_CACHE = 'fortigate-nextrade-dynamic-v1';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/static/css/nextrade-complete.css',
  '/static/css/layout-improvements.css',
  '/static/css/ui-enhancements.css',
  '/static/css/websocket-enhancements.css',
  '/static/js/main.js',
  '/static/js/ui-enhancements.js',
  '/static/js/websocket-enhanced.js',
  '/static/js/dashboard-realtime.js',
  '/static/img/fortigate/fortigate-logo.svg',
  '/static/img/nextrade/logo_new.svg',
  '/static/vendor/fonts/pretendard.css',
  '/offline.html'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch(err => console.error('Error caching static assets:', err))
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(cacheName => {
              return cacheName.startsWith('fortigate-nextrade-') && 
                     cacheName !== CACHE_NAME &&
                     cacheName !== DYNAMIC_CACHE;
            })
            .map(cacheName => {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip WebSocket connections
  if (url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }
  
  // Skip API requests (always fetch from network)
  if (url.pathname.startsWith('/api/') || 
      url.pathname.startsWith('/socket.io/')) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // Return a custom offline response for API requests
          return new Response(
            JSON.stringify({ error: 'Offline', message: '네트워크 연결이 필요합니다.' }),
            { 
              headers: { 'Content-Type': 'application/json' },
              status: 503
            }
          );
        })
    );
    return;
  }
  
  // For HTML requests, use network-first strategy
  if (request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone the response before caching
          const responseToCache = response.clone();
          
          caches.open(DYNAMIC_CACHE)
            .then(cache => cache.put(request, responseToCache));
          
          return response;
        })
        .catch(() => {
          return caches.match(request)
            .then(response => {
              if (response) {
                return response;
              }
              // Return offline page for navigation requests
              if (request.mode === 'navigate') {
                return caches.match('/offline.html');
              }
            });
        })
    );
    return;
  }
  
  // For other assets, use cache-first strategy
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          // Return from cache but also fetch and update
          fetch(request)
            .then(fetchResponse => {
              caches.open(DYNAMIC_CACHE)
                .then(cache => cache.put(request, fetchResponse));
            })
            .catch(() => {}); // Silently fail
          
          return response;
        }
        
        // Not in cache, fetch from network
        return fetch(request)
          .then(fetchResponse => {
            // Don't cache non-successful responses
            if (!fetchResponse || fetchResponse.status !== 200 || 
                fetchResponse.type !== 'basic') {
              return fetchResponse;
            }
            
            const responseToCache = fetchResponse.clone();
            
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(request, responseToCache));
            
            return fetchResponse;
          });
      })
      .catch(() => {
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
          return caches.match('/offline.html');
        }
      })
  );
});

// Background sync for offline form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-analysis') {
    event.waitUntil(syncAnalysisRequests());
  }
});

async function syncAnalysisRequests() {
  try {
    // Get pending requests from IndexedDB
    const pendingRequests = await getPendingRequests();
    
    for (const request of pendingRequests) {
      try {
        const response = await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body
        });
        
        if (response.ok) {
          // Remove from pending requests
          await removePendingRequest(request.id);
          
          // Notify client of successful sync
          self.clients.matchAll().then(clients => {
            clients.forEach(client => {
              client.postMessage({
                type: 'sync-complete',
                requestId: request.id
              });
            });
          });
        }
      } catch (error) {
        console.error('Sync failed for request:', request.id, error);
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// Push notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : '새로운 알림이 있습니다.',
    icon: '/static/img/icons/icon-192x192.png',
    badge: '/static/img/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: '확인하기',
        icon: '/static/img/icons/checkmark.png'
      },
      {
        action: 'close',
        title: '닫기',
        icon: '/static/img/icons/close.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('FortiGate Analyzer', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'explore') {
    // Open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Helper functions for IndexedDB (simplified)
async function getPendingRequests() {
  // Implementation would use IndexedDB to store/retrieve pending requests
  return [];
}

async function removePendingRequest(id) {
  // Implementation would remove request from IndexedDB
  return true;
}

// Message handling from clients
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    const urlsToCache = event.data.payload;
    caches.open(DYNAMIC_CACHE)
      .then(cache => cache.addAll(urlsToCache));
  }
});