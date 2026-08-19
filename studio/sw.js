// ==========================================================================
// TOAN AAS PWA SERVICE WORKER — OFFLINE CACHE & INSTANT STANDALONE LAUNCH
// ==========================================================================

const CACHE_NAME = 'toanaas-pwa-v3.0';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './style.css',
  './script.js',
  './manifest.json',
  './assets/toanaas_logo.jpg',
  './assets/toanaas_banner_wide.png',
  './assets/toanaas_banner_cinematic.jpg',
  './assets/toanaas_bot_avatar.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => {
      return res || fetch(e.request).catch(() => caches.match('./index.html'));
    })
  );
});
