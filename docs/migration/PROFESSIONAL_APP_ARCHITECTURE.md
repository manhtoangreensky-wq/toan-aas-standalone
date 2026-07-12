# Professional App Architecture

## Product decision

`app.toanaas.vn` is an application origin, not the marketing website. Its
entry contract is intentionally simple:

| Visitor state | Route `/` / `/app` |
| --- | --- |
| No signed session | `/login` |
| Signed Web account (with or without Telegram) | `/dashboard` |

The optional product introduction is `/welcome`. It must not be the default
experience for an application user. Railway health checks `/health`, never a
redirecting application route.

## Why the backend remains FastAPI

The current Python service is the Web product backend for signed sessions,
CSRF, ownership checks, Project Center and Studio Documents. Telegram Bot is
an optional connector—not the authority for Web-owned work. Rewriting this
backend in Java would not improve the UI and would risk duplicating its
security boundaries while the independent Web core is still evolving.

Java can be evaluated later for a distinct service with a proven need. It is
not an appropriate replacement for the safety-critical Web backend during the
current independent-product build.

## Independent capability plane

The Web App is allowed to exceed Telegram's interaction limits. It owns a
Project Center where a signed account can create Projects and versioned Studio
Documents (briefs, prompts, captions, scripts, storyboards and content packs)
without a Telegram link, Bot bridge, provider call, PayOS request or Xu
mutation. Every mutation is server-side CSRF protected, idempotent,
owner-scoped and audited; document edits use optimistic revision control and
restore creates a new revision instead of deleting history.

Bot integrations stay optional and clearly separated. Wallet, existing PayOS
webhook flows, provider execution and Bot-origin job/delivery adapters remain
guarded until their Web-native replacements are individually designed and
tested. The browser still never holds a ledger, payment authority, provider
secret or raw Telegram identity.

### Studio behavior before an engine is enabled

Every signed Web account can use a draft-supported Studio route as a real
authoring surface. If no Engine Web capability is present, the primary submit
action saves or updates the account-owned Web draft; pressing Enter performs
the same safe write. It does not send data to Telegram, a provider, PayOS or
the legacy bridge. A Bot companion may be shown only as an optional, no-data
shortcut for customers who choose it. Estimate, charge, job creation and
delivery remain unavailable until their own Web-native or integration contract
is enabled and verified.

## Application shell

The signed shell is organized around how a customer works rather than a long
list of commands:

1. **Workspace** — overview, Project Center, Web drafts, content plans,
   calendar and self-review.
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
- External engine features preserve `draft → estimate → confirm → queued →
  processing → completed/failed/guarded`, with a separately audited Web-native
  engine or optional integration responsible for any job, charge or private
  delivery URL. Project/Studio authoring is intentionally a different,
  immediate Web-owned capability and never claims to be media output.
