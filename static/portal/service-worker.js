/* Only public portal shell assets are cached.  API, wallet, payment, admin,
   uploads and private delivery URLs are intentionally never cached. */
const CACHE_NAME = "toan-aas-portal-shell-v1";
const SHELL = [
  "/static/portal/portal.css",
  "/static/portal/portal.js",
  "/static/portal/integration.js",
  "/static/portal/manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.startsWith("/static/portal/")) return;
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
    if (!response || !response.ok || response.type !== "basic") return response;
    const copy = response.clone();
    caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
    return response;
  })));
});
