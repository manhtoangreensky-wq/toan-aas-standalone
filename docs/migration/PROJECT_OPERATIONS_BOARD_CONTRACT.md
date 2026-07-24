# Project Operations Board — canonical Web-native contract

## Purpose and canonical routes

`/projects` is the canonical **Project Operations Board** for a signed Web
account. It is the compact operational view for a private Project library; it
does not introduce `/project-hub`, a second Project store, a generic feature
runner or a Bot compatibility route.

| Route | Role | Authority |
| --- | --- | --- |
| `/projects` | app-first board: current-page metrics, private library, filters and paging | existing signed Project list API |
| `/projects/new` | focused Project authoring form | existing CSRF/idempotent Project create contract |
| `/projects/{uuid}` | Project Workspace/detail, Studio Documents and revision history | existing server owner/revision checks |

The `/projects/new` route does not accept a Project ID, form text, Bot state,
reference, provider request or execution instruction through its URL. A
created Project ID appears only in the server receipt and is then used for the
private detail route.

An unsent `/projects/new` form is tab-memory only. It is cleared on every
server bootstrap, sign-out and back-forward-cache rehydration before the next
signed account projection is rendered. It is never copied to browser storage,
the URL, a Bot, the bridge or the PWA cache.

## Existing read and write model; no new backend surface

The root board reuses the existing owner-scoped reader:

- `GET /api/v1/projects?limit=50&offset=…`
- existing bounded `q` and `state` filter parameters

Focused authoring uses the existing write only:

- `POST /api/v1/projects` with signed session, CSRF and idempotency key

No database table, migration, API namespace, background worker, provider
adapter, upload flow, job, payment path or bridge read model is added. The
server remains authoritative for account ownership, field validation, query
validation, pagination, CSRF, idempotency, revision history and audit events.

## Truthful board state and counts

The `/projects` board observes `projectCenterReadState`:

1. **guarded** — no signed Project read capability; no prior workspace, Bot
   Project or browser substitute is rendered.
2. **loading** — the existing owner-scoped list is loading. Private records
   remain cleared instead of being replaced with stale cards.
3. **ready** — the current server list projection may be displayed.
4. **failed** — the list projection is cleared and an explicit signed retry is
   available. The page does not invent a timeline, all-workspace total, Bot
   activity or provider result.

All metrics are explicitly limited to the **current list page** because the
existing list API is the only source in this PR; no summary endpoint is
invented for UI convenience. Filters and paging remain session-local and are
never copied into the URL, Telegram, browser storage or PWA cache.

## Permission and execution boundary

A view-only signed session sees a clear non-clickable creation explanation.
It is never sent from a live-looking create CTA to a disabled form. The direct
authoring route remains server-gated and visually reports its guarded write
state when CSRF/write capability is unavailable.

Project Center is a Web-native authoring boundary. It has no Bot bridge,
Telegram identity mutation, provider call, AI output claim, job, Xu ledger,
PayOS order, payment webhook, publish, media delivery or notification side
effect. Studio Document editing and Project Package export keep their existing
separate contracts and are not changed by this board PR.

## Private PWA policy

`/projects` and `/api/v1/projects` are explicit private Service Worker
prefixes, which also cover `/projects/new` and `/projects/{uuid}`. They never
enter the public shell cache or offline fallback across sign-out/account
switching.

## Focused acceptance checks

- Root board, focused `/new` form and `{uuid}` detail retain distinct
  responsibilities and canonical paths.
- Root list failures clear private records and offer an honest retry without a
  Bot/cache fallback.
- All numbers are clearly labeled as current-page values.
- No fabricated recent activity, provider result or execution status appears.
- Mobile controls retain a 44px minimum, keyboard focus remains visible and
  reduced motion removes board-card transforms.
- No Bot, provider, wallet, PayOS, job, webhook, database or API changes are
  included in this UI-only PR.
