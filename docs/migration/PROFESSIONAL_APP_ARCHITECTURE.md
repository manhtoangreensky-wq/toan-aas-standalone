# Professional App Architecture

## Product decision

`app.toanaas.vn` is an application origin, not the marketing website. Its
entry contract is intentionally simple:

| Visitor state | Route `/` / `/app` |
| --- | --- |
| No signed session | `/login` |
| Signed but not linked to canonical Telegram identity | `/onboarding` |
| Signed and linked | `/dashboard` |

The optional product introduction is `/welcome`. It must not be the default
experience for an application user. Railway health checks `/health`, never a
redirecting application route.

## Why the backend remains FastAPI

The current Python service is the Web BFF for signed sessions, CSRF, upload
validation, ownership checks and the private Bot bridge. Rewriting it in Java
would not improve the UI and would risk duplicating or weakening the canonical
Bot boundaries for Telegram identity, Xu ledger, PayOS, jobs and providers.

Java can be evaluated later for a distinct service with a proven need. It is
not an appropriate replacement for the safety-critical Web BFF during Bot
feature parity work.

## Application shell

The signed shell is organized around how a customer works rather than a long
list of commands:

1. **Workspace** — overview, Web drafts, content plans, calendar and
   self-review.
2. **Create** — studio hubs for Content, Image, Video, Voice & Music, and
   Language & Documents.
3. **Work** — canonical Job Center and owner-scoped Assets.
4. **Wallet & plans** — read-only Xu/plan data and canonical top-up handoff.
5. **Account & help** — identity, activity, tickets, support and service
   status.
6. **Bot companion** — Telegram-first Notes, Reminders, Referrals, Rewards,
   Community and Guides, clearly labelled as Bot-owned handoffs.

The dashboard focuses on actual state only: owner-scoped Web drafts,
canonical processing jobs and assets with a validated delivery contract. It
does not invent notifications, job completion, wallet balances or provider
results in the browser.

## TypeScript migration path

The existing `portal.js` presentation layer and `integration.js` signed API
layer are kept stable while the UI is migrated incrementally. Do not put a
Node package manifest at the repository root without an explicit Railway build
plan: the production service is currently Python/Nixpacks.

1. Split the current browser code into ES modules under `frontend/` while
   retaining the same server-rendered portal shell and same-origin URLs.
2. Add TypeScript contracts for the safe envelope, catalog, session,
   workspace draft, job and asset projections. Run `tsc --noEmit` in CI.
3. Move the application shell, navigation and dashboard into TypeScript
   components first; preserve current Portal pages as the feature-parity
   fallback until each route is verified.
4. Introduce React/Vite only behind a deliberate build path (prefer a
   multi-stage container: Node build then Python runtime serving static
   output). Keep the final app same-origin so HttpOnly cookies, CSRF and CSP
   do not acquire a second trust boundary.
5. Add browser smoke tests for login, Telegram onboarding, admin protection,
   owner-scoped Jobs/Assets, payment guards and mobile navigation before
   switching a production route.

## Non-negotiable browser boundaries

- No Bot/provider/PayOS request directly from browser code.
- No browser ledger, credit, webhook or payment finalization.
- No raw Telegram ID, session token, bridge HMAC or provider secret in UI
  state or local storage.
- The service worker may cache only public hashed shell assets; never signed
  bootstrap, API, admin, wallet, payment or private file responses.
- Every feature preserves `draft → estimate → confirm → queued → processing →
  completed/failed/guarded`, where only the Bot canonical side can create or
  finalize a job, charge Xu or release a private delivery URL.
