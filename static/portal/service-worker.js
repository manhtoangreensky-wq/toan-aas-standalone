/* Only public portal shell assets are cached. API, wallet, payment, admin,
   uploads, /api/v1/asset-vault, /api/v1/project-packages,
   /api/v1/document-operations and private delivery
   URLs are intentionally never cached. */
const CACHE_NAME = "toan-aas-portal-shell-v4";
const SHELL = Object.freeze([
  "/static/portal/portal.css",
  "/static/portal/portal.js",
  "/static/portal/integration.js",
  "/static/portal/manifest.webmanifest"
]);
const SHELL_PATHS = new Set(SHELL);

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  // Never turn a broad static folder into an implicit cache policy.  Only the
  // fixed public shell above can be served from Cache Storage; API responses,
  // signed file URLs and any future private/static asset fall through to the
  // browser's normal network path without being persisted by this worker.
  if (request.method !== "GET" || url.origin !== self.location.origin || !SHELL_PATHS.has(url.pathname)) return;
  // Network-first is intentional for the portal shell. A PWA must not keep a
  // stale login/link UI after a deploy (especially when auth recovery fixes
  // land). The pre-cached shell remains a public offline fallback only.
  event.respondWith(fetch(request).catch(() => caches.match(url.pathname).then((cached) => cached || Response.error())));
});
