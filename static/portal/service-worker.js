/* Only public portal shell assets are cached. API, wallet, payment, admin,
   Support Desk cases/messages, Prompt Library templates/previews/exports,
   Audio Library & Briefing collections/briefs/Asset Vault references, Audio
   Production Hub projections, Creative
   Content Studio briefs/content pieces/history, Voice Studio consent metadata/
   scripts/cue sheets/history, uploads,
   /api/v1/asset-vault, /api/v1/project-packages, /api/v1/document-operations,
   /api/v1/admin/internal-documents
   (including private Image OCR),
   /api/v1/image-operations, /api/v1/account/data-controls (including export
   attachments and erasure-review receipts), /api/v1/media-workspace (including Music Prompt
   Composer), /api/v1/content-studio, /api/v1/channel-strategy,
   /api/v1/content-handoffs and /api/v1/partner-crm
   (including the stateless Content Prompt Pack draft endpoint),
    /api/v1/trend-research (manual research receipts only),
    /api/v1/growth-review (manual, account-private Growth Review input and receipt),
   /api/v1/media-factory (transient Media Factory blueprints only),
   /api/v1/quick-image-planner (transient Quick Image prompt plans only),
   /api/v1/voice-studio, /api/v1/video-studio (including the prompt planner), /api/v1/image-studio, /api/v1/subtitle-studio,
   /api/v1/document-workspace, /api/v1/chat-workspace, /api/v1/analytics-workspace, /api/v1/workboard,
    /api/v1/workspace/setup, /api/v1/workspace/starter-kits,
    /api/v1/operations, /internal/v1/operations, /api/v1/inbox, /internal/v1/notifications,
    private `/image-studio/*` routes and private `/image-hub/*` routes, private `/image/prompt-composer` route, private `/voice-studio/direction-composer`, private `/video-studio/prompt-planner`, `/video-studio/cinematic-concept`, `/video-studio/motion-guide`, `/video-studio/image-motion-planner`, `/video-studio/reference-format-planner` and `/video-studio/storyboard-composer` routes, private `/media-workspace/*`, private `/audio-hub/*`, private `/document-workspace/*` routes, private `/documents/ocr`, `/documents/pdf-ocr` and `/documents/pdf-ocr-to-word` routes,
     private `/chat/*` routes, private `/analytics/*` routes, private `/free-prompt-gallery` and `/api/v1/free-prompt-gallery`, private `/guides` and `/api/v1/guides`, private `/content/channel-strategy`, `/content/prompt-pack`, `/content/publish-review`, `/content/contextual-prompt`, `/trend-research`, `/media-factory`, `/creative-flow`, `/video-studio/workflow`, `/video-studio/story-video-plan` and `/guides/source-rights` routes, private `/workboard/*` routes,
     private `/content/handoffs/*`, private `/crm/*`, private `/operations/*`, private `/admin/operations/*`, private `/admin/reliability/*`, private `/inbox/*`, private `/automation/*` and private `/workspace-menu` routes and private delivery URLs are
    private `/starter-kits/*` routes and private delivery URLs are intentionally
    never cached. */
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
  "/static/portal/portal-i18n.js",
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
  // Asset Vault metadata, private downloads and same-origin Blob previews are
  // owner-scoped. Keep both the API and inspector page explicit even though
  // SHELL is already an allow-list, so a future cache expansion cannot retain
  // a video Blob response after sign-out or an account switch.
  "/" + "api/v1/asset-vault",
  "/asset-vault",
  "/video/preview",
  "/" + "api/v1/document-operations",
  // Document Studio now includes an owner-scoped combined operation history.
  // Keep the entire route family explicit so a future shell expansion cannot
  // replay a prior account's operation metadata after sign-out or switching.
  "/documents",
  "/documents/ocr",
  "/documents/pdf-ocr",
  "/documents/pdf-ocr-to-word",
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
  // Guide Center follows signed interface locale and must never retain a
  // prior account's snapshot in Cache Storage, even though it is read-only.
  "/" + "api/v1/guides",
  "/guides",
  // Content Operations Board projects signed-account summary, activity,
  // references and brief metadata. Keep the canonical page family explicit so
  // a future public-shell expansion cannot replay a prior account's content.
  "/" + "api/v1/content-studio",
  "/content-studio",
  // Projects carry signed owner-scoped authoring metadata and are also used
  // as reference pickers. Keep root, `/new` and detail descendants outside
  // public shell/offline caching across sign-out or account switching.
  "/" + "api/v1/projects",
  "/projects",
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
  // Quick Image Planner returns a signed session's private custom brief and
  // optional watermark direction. Keep its page and API explicit no-cache
  // paths even though the shell cache is already allow-listed.
  "/" + "api/v1/quick-image-planner",
  "/image/quick-planner",
  "/creative-flow",
  "/video-studio/workflow",
  "/video-studio/story-video-plan",
  "/guides/source-rights",
  "/" + "api/v1/media-workspace",
  // Audio Production Hub is an account-private visual projection over the
  // owner-scoped Media Workspace API. Keep every route out of Cache Storage;
  // no collection brief, Asset Vault reference or revision may survive a
  // sign-out/account switch through a public PWA shell cache.
  "/media-workspace",
  "/audio-hub",
  "/media-workspace/music-prompt-composer",
  "/media-workspace/music-directions",
  "/media-workspace/sfx-cue-sheet",
  // Image Operations Hub is a private visual projection over signed Image
  // Studio data. Its artboard metadata must never be reachable through a
  // public shell/offline fallback after sign-out or account switching.
  "/image-hub",
  "/image/prompt-composer",
  "/" + "api/v1/voice-studio",
  "/voice-studio/direction-composer",
  "/" + "api/v1/video-studio",
  "/video-studio/prompt-planner",
  "/video-studio/cinematic-concept",
  // Creative Motion Guide renders account-scoped transient planning drafts
  // and must never become a shell/offline cache entry after sign-out or an
  // account switch. Its API is already covered by /api/v1/video-studio.
  "/video-studio/motion-guide",
  "/video-studio/image-motion-planner",
  "/video-studio/reference-format-planner",
  "/video-studio/storyboard-composer",
  "/" + "api/v1/workboard",
  "/workboard",
  // Subtitle Studio includes owner-scoped transcript drafts and the new
  // metadata-only language-source picker. Name both paths explicitly, even
  // though the worker caches only a fixed public shell, so later cache-policy
  // expansion cannot retain another account's source metadata or drafts.
  "/" + "api/v1/subtitle-studio",
  "/subtitle-studio",
  // First-run Workspace Setup contains signed-account choices and revision
  // metadata. Keep both API and page outside Cache Storage even if the public
  // shell allow-list evolves in a future release.
  "/" + "api/v1/workspace/setup",
  "/workspace/setup",
  // Onboarding and Account contain signed-session state, login-method
  // metadata and one-time Telegram-link presentation. They are never an
  // offline/public PWA fallback, including all Account child routes.
  "/onboarding",
  "/account",
  // Workspace Menu has no route-specific API, but the catalog and signed
  // session still make it account-private. Keep it explicit so a future PWA
  // cache expansion cannot turn it into a public offline destination.
  "/workspace-menu",
  // Dashboard combines signed Web workspace metadata with canonical bridge
  // reads. It must never become a public shell/offline fallback after logout,
  // account switching or a failed canonical refresh.
  "/dashboard",
  // Starter Kits expose owner-scoped setup revisions and install receipts.
  // Keep the catalog/API and every fixed detail page out of Cache Storage.
  "/" + "api/v1/workspace/starter-kits",
  "/starter-kits",
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
  // The binary Admin Internal Document Archive is a private local-admin
  // surface. Name it independently of the broad /admin guard so page/API
  // additions cannot ever fall back to an account-agnostic PWA shell.
  "/" + "api/v1/admin/internal-documents",
  "/admin/internal-documents",
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
