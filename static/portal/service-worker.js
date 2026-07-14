/* Only public portal shell assets are cached. API, wallet, payment, admin,
   Support Desk cases/messages, Prompt Library templates/previews/exports,
   Audio Library & Briefing collections/briefs/Asset Vault references, Creative
   Content Studio briefs/content pieces/history, Voice Studio consent metadata/
   scripts/cue sheets/history, uploads,
   /api/v1/asset-vault, /api/v1/project-packages, /api/v1/document-operations,
   /api/v1/image-operations, /api/v1/media-workspace, /api/v1/content-studio,
   /api/v1/voice-studio, /api/v1/video-studio, /api/v1/image-studio, /api/v1/subtitle-studio,
   /api/v1/document-workspace, /api/v1/chat-workspace, /api/v1/analytics-workspace,
   private `/image-studio/*` routes, private `/document-workspace/*` routes,
   private `/chat/*` routes, private `/analytics/*` routes and private delivery URLs are
   intentionally never cached. */
const CACHE_NAME = "toan-aas-portal-shell-v15";
const SHELL = Object.freeze([
  "/static/portal/portal.css",
  "/static/portal/portal.js",
  "/static/portal/integration.js",
  "/static/portal/manifest.webmanifest"
]);
const SHELL_PATHS = new Set(SHELL);
// This is deliberately redundant with the fixed SHELL allow-list.  Naming
// new private workspace families here makes their no-cache contract resilient
// if the public shell grows later: document brief/plan metadata must never be
// returned from Cache Storage after a user signs out or switches accounts.
const PRIVATE_PATH_PREFIXES = Object.freeze([
  "/" + "api/v1/document-workspace",
  "/document-workspace",
  "/" + "api/v1/chat-workspace",
  "/chat",
  "/" + "api/v1/analytics-workspace",
  "/analytics"
]);

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
  const isPrivatePath = PRIVATE_PATH_PREFIXES.some((prefix) => url.pathname === prefix || url.pathname.startsWith(prefix + "/"));
  if (request.method !== "GET" || url.origin !== self.location.origin || isPrivatePath || !SHELL_PATHS.has(url.pathname)) return;
  // Network-first is intentional for the portal shell. A PWA must not keep a
  // stale login/link UI after a deploy (especially when auth recovery fixes
  // land). The pre-cached shell remains a public offline fallback only.
  event.respondWith(fetch(request).catch(() => caches.match(url.pathname).then((cached) => cached || Response.error())));
});
