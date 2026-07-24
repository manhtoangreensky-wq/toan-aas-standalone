# Campaign Operations Board — canonical Web-native contract

## Purpose and canonical routes

`/campaigns` is the canonical **Campaign Operations Board** for a signed Web
account. It is a compact, owner-scoped planning library rather than a Bot
campaign mirror, publisher, performance dashboard or generic automation
surface.

| Route | Role | Authority |
| --- | --- | --- |
| `/campaigns` | app-first board: loaded-projection metrics, private library and links to adjacent planning views | existing signed Campaign list API |
| `/campaigns/new` | focused Campaign authoring form | existing CSRF/idempotent Campaign create contract |
| `/campaigns/{uuid}` | existing detail: brief, self-review, lifecycle and explicit in-app schedule intent | existing server owner/revision checks |
| `/calendar` | independent bounded calendar window | existing owner-scoped calendar API |
| `/approvals` | existing personal self-review queue | existing signed Campaign list API |

The `/campaigns/new` route accepts no Campaign ID, title, Bot state, Telegram
identity, provider request, publication instruction or prefill through the
URL. A Campaign ID is used only after a valid server receipt returns it.

An unsent `/campaigns/new` form is tab-memory only. It is cleared on server
bootstrap, sign-out and back-forward-cache rehydration before the next signed
account projection appears. It never enters browser storage, the URL, a Bot,
bridge, provider request or PWA cache.

## Existing read and write model; no new backend surface

The board reuses only the current Web-owned Campaign model:

- `GET /api/v1/campaigns`
- `POST /api/v1/campaigns` with signed session, CSRF and idempotency key
- `GET /api/v1/campaigns/{uuid}`
- `PATCH /api/v1/campaigns/{uuid}`
- `POST /api/v1/campaigns/{uuid}/status`

No database table, migration, API namespace, scheduler semantic, publish
queue, provider adapter, channel credential, job, payment path, bridge read
model or admin Campaign authority is added. Detail, Calendar and Self-review
retain their existing independent responsibilities.

## Truthful root state and counts

The root board observes `campaignPlannerReadState`:

1. **guarded** — no signed Campaign read capability or signed session.
2. **loading** — the list request is active. Existing cards are cleared before
   the request so a prior account/list cannot remain actionable.
3. **ready** — only the current server projection is displayed.
4. **failed** — the list is cleared and the user can issue an explicit signed
   retry. The board does not substitute Bot Campaigns, browser cache, provider
   data or invented activity.

All numbers explicitly mean **the loaded/current projection**. The existing
list contract has no global summary endpoint, so this PR never claims an
all-workspace total, current publication state, performance, revenue or
recent activity.

## Bot parity disposition

Bot planning commands and callbacks are reference evidence only. The Web
board preserves the useful planning shape—brief, lifecycle, calendar and
self-review—without importing Bot conversation/pending state, Telegram
identity, channel configuration, publisher queue, performance records,
financial data or administrative approval state. Bot source is not edited.

## Private PWA policy

The existing `/campaigns` and `/api/v1/campaigns` Service Worker private
prefixes cover the root, `/campaigns/new` and UUID detail descendants. They
remain outside the public shell cache and offline fallback across sign-out or
account switching.

## Focused acceptance checks

- Root board, focused `/new` form and UUID detail have distinct roles and
  exact server-routable paths.
- Root refresh clears private cards before a new signed read and never leaves
  a stale card actionable.
- Root card actions only open owner-scoped detail; edit, status and schedule
  controls stay on existing detail routes.
- Metrics say loaded/current projection and no activity/publish/performance
  result is fabricated.
- Mobile controls retain a 44px minimum, keyboard focus stays visible and
  reduced motion removes card movement.
- No Bot, provider, wallet, PayOS, job, webhook, database, API or scheduler
  change is included in this UI-flow PR.
