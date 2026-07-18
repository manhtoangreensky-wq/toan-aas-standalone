/* Only public portal shell assets are cached. API, wallet, payment, admin,
   Support Desk cases/messages, Prompt Library templates/previews/exports,
   Audio Library & Briefing collections/briefs/Asset Vault references, Creative
   Content Studio briefs/content pieces/history, Voice Studio consent metadata/
   scripts/cue sheets/history, uploads,
   /api/v1/asset-vault, /api/v1/project-packages, /api/v1/document-operations
   (including private Image OCR),
   /api/v1/image-operations, /api/v1/account/data-controls (including export
   attachments and erasure-review receipts), /api/v1/media-workspace (including Music Prompt
   Composer), /api/v1/content-studio, /api/v1/channel-strategy,
   /api/v1/content-handoffs and /api/v1/partner-crm
   (including the stateless Content Prompt Pack draft endpoint),
    /api/v1/trend-research (manual research receipts only),
    /api/v1/growth-review (manual, account-private Growth Review input and receipt),
    /api/v1/media-factory (transient Media Factory blueprints only),
   /api/v1/voice-studio, /api/v1/video-studio (including the prompt planner), /api/v1/image-studio, /api/v1/subtitle-studio,
    /api/v1/document-workspace, /api/v1/chat-workspace, /api/v1/analytics-workspace, /api/v1/workboard,
    /api/v1/operations, /internal/v1/operations, /api/v1/inbox, /internal/v1/notifications,
    private `/image-studio/*` routes, private `/image/prompt-composer` route, private `/voice-studio/direction-composer`, `/video-studio/prompt-planner`, `/video-studio/cinematic-concept`, `/video-studio/image-motion-planner`, `/video-studio/reference-format-planner` and `/video-studio/storyboard-composer` routes, private `/media-workspace/music-prompt-composer`, private `/document-workspace/*` routes, private `/documents/ocr` and `/documents/pdf-ocr` routes,
     private `/chat/*` routes, private `/analytics/*` routes, private `/free-prompt-gallery` and `/api/v1/free-prompt-gallery`, private `/content/channel-strategy`, `/content/prompt-pack`, `/content/publish-review`, `/content/contextual-prompt`, `/trend-research`, `/media-factory`, `/creative-flow`, `/video-studio/workflow`, `/video-studio/story-video-plan` and `/guides/source-rights` routes, private `/workboard/*` routes,
    private `/content/handoffs/*`, private `/crm/*`, private `/operations/*`, private `/admin/operations/*`, private `/admin/reliability/*`, private `/inbox/*` and private `/automation/*` routes and private delivery URLs are
    intentionally never cached. */
// Cache Storage is origin-wide.  Only remove obsolete generations created by
// this worker; other applications sharing the origin may own their own caches.
const CACHE_PREFIX = "toan-aas-portal-shell-";
const BUILD_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/;
const LOCAL_BUILD_ID = "local";

function workerBuildId() {
  // The worker obtains its cache generation from its own script URL, not from
  // a page/global that an older client could retain.  Invalid, missing or
  // overlong parameters deliberately collapse to one deterministic local
  // generation rather than becoming a cache-key injection surface.
  const candidate = new URL(self.location.href).searchParams.get("build") || "";
  return BUILD_ID_PATTERN.test(candidate) ? candidate : LOCAL_BUILD_ID;
}

const BUILD_ID = workerBuildId();
const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;
const OFFLINE_FALLBACK = "/static/portal/offline.html";
// The cache is an explicit allow-list, never a runtime cache.  It contains
// only public, account-free shell files plus a generic offline notice.
const SHELL = Object.freeze([
  "/static/portal/portal.css",
  "/static/portal/portal.js",
  "/static/portal/integration.js",
  "/static/portal/manifest.webmanifest",
  "/static/portal/app-icon.svg",
  OFFLINE_FALLBACK
]);
const SHELL_PATHS = new Set(SHELL);
// The page requests versioned assets as well.  Seed this generation with an
// explicit build query and `cache: reload` so an HTTP cache from an earlier
// deploy cannot supply a mixed shell while the new worker installs.
const SHELL_CACHE_REQUESTS = Object.freeze(
  SHELL.map((path) => new Request(`${path}?build=${encodeURIComponent(BUILD_ID)}`, { cache: "reload" }))
);
// Offline fallback intentionally applies only to routes that are public even
// without a signed session.  In particular, it never substitutes a generic
// response for a dashboard, account, wallet, admin or any API request.
const PUBLIC_NAVIGATION_PATHS = Object.freeze([
  "/welcome",
  "/legal",
  "/privacy",
  "/login",
  "/register"
]);
// This is deliberately redundant with the fixed SHELL allow-list.  Naming
// new private workspace families here makes their no-cache contract resilient
// if the public shell grows later: document brief/plan metadata must never be
// returned from Cache Storage after a user signs out or switches accounts.
const PRIVATE_PATH_PREFIXES = Object.freeze([
  "/" + "api/v1/document-operations",
  "/documents/ocr",
  "/documents/pdf-ocr",
   "/" + "api/v1/document-workspace",
   "/document-workspace",
  // Data Control Center exposes signed account-private inventory, review
  // receipts and a direct no-store export attachment. It is never a shell
  // cache entry or offline fallback, including future child routes.
  "/" + "api/v1/account/data-controls",
  "/account/data-controls",
   "/" + "api/v1/chat-workspace",
  "/chat",
  "/" + "api/v1/analytics-workspace",
  "/analytics",
  "/" + "api/v1/free-prompt-gallery",
  "/free-prompt-gallery",
  "/" + "api/v1/content-studio",
  "/" + "api/v1/channel-strategy",
  "/content/channel-strategy",
  "/" + "api/v1/content-handoffs",
  "/content/handoffs",
  "/" + "api/v1/partner-crm",
  "/crm",
  "/content/prompt-pack",
  "/content/publish-review",
  "/content/contextual-prompt",
  "/" + "api/v1/trend-research",
  "/trend-research",
  // Growth Review accepts account-private manual performance input and returns
  // a transient receipt. Keep both its page and API explicit no-cache paths;
  // the shell allow-list is intentionally not the security boundary here.
  "/" + "api/v1/growth-review",
  "/growth/ai",
  "/" + "api/v1/media-factory",
  "/media-factory",
  "/creative-flow",
  "/video-studio/workflow",
  "/video-studio/story-video-plan",
  "/guides/source-rights",
  "/" + "api/v1/media-workspace",
  "/media-workspace/music-prompt-composer",
  "/image/prompt-composer",
  "/" + "api/v1/voice-studio",
  "/voice-studio/direction-composer",
  "/" + "api/v1/video-studio",
  "/video-studio/prompt-planner",
  "/video-studio/cinematic-concept",
  "/video-studio/image-motion-planner",
  "/video-studio/reference-format-planner",
  "/video-studio/storyboard-composer",
  "/" + "api/v1/workboard",
  "/workboard",
  // Campaign Planner, its Calendar and self-review views are signed
  // account-owned planning surfaces. Campaign schedule intents are private
  // Inbox metadata, never a public PWA cache entry or offline fallback.
  "/" + "api/v1/campaigns",
  "/campaigns",
  "/calendar",
  "/approvals",
  "/" + "api/v1/operations",
  // Governance Documents contains private local-admin drafts, review notes,
  // immutable versions and audit projections. Keep it named explicitly in
  // addition to the broader /admin rule so a future route refactor cannot
  // accidentally make this family eligible for a shell/offline fallback.
  "/" + "api/v1/admin/governance",
  "/admin/governance",
  "/" + "api/v1/admin",
  "/" + "internal/v1/operations",
  "/operations",
  "/admin",
  "/admin/operations",
  "/admin/autopilot",
  "/admin/reliability",
  "/" + "api/v1/inbox",
  "/" + "internal/v1/notifications",
  "/inbox",
  "/automation"
]);

self.addEventListener("install", (event) => {
  // Do not skip the waiting lifecycle.  A live form or editor keeps its
  // current controller until the browser naturally retires the old worker;
  // the online page itself is already network-first and can reload normally.
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_CACHE_REQUESTS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
  );
});

function matchCurrentShell(path) {
  // Cache Storage is origin-wide.  Restrict every offline lookup to this
  // exact build generation; another portal generation cannot be used as a
  // fallback after a deploy.  `ignoreSearch` joins versioned page URLs to the
  // fixed public allow-list without making arbitrary URL query values cacheable.
  return caches.open(CACHE_NAME).then((cache) => cache.match(path, { ignoreSearch: true }));
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  // Never turn a broad static folder into an implicit cache policy.  Only the
  // fixed public shell above can be served from Cache Storage; API responses,
  // signed file URLs and any future private/static asset fall through to the
  // browser's normal network path without being persisted by this worker.
  const isPrivatePath = PRIVATE_PATH_PREFIXES.some((prefix) => url.pathname === prefix || url.pathname.startsWith(prefix + "/"));
  if (request.method !== "GET" || url.origin !== self.location.origin || isPrivatePath) return;
  // A navigation fallback is safe only for a fixed list of public routes. It
  // is never a cache fallback for API calls or any private workspace route.
  if (request.mode === "navigate") {
    if (!PUBLIC_NAVIGATION_PATHS.includes(url.pathname)) return;
    event.respondWith(fetch(request).catch(() => matchCurrentShell(OFFLINE_FALLBACK).then((cached) => cached || Response.error())));
    return;
  }
  if (!SHELL_PATHS.has(url.pathname)) return;
  // Network-first is intentional for the portal shell. A PWA must not keep a
  // stale login/link UI after a deploy (especially when auth recovery fixes
  // land). The pre-cached shell remains a public offline fallback only.
  event.respondWith(fetch(request).catch(() => matchCurrentShell(url.pathname).then((cached) => cached || Response.error())));
});
