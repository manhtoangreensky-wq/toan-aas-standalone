# Content Operations Board — canonical Web-native contract

## Purpose and canonical routes

`/content-studio` is the canonical **Content Operations Board** for a signed
Web account. This change upgrades the existing Content Studio root; it does
not introduce `/content-hub`, a second authoring store, a generic feature
runner or a Bot compatibility route.

| Route | Role | Authority |
| --- | --- | --- |
| `/content-studio` | app-first board: summary, allowlisted brief starts, owner-scoped brief library and audit-safe activity | existing signed Content Studio APIs |
| `/content-studio/new` | focused Content Brief authoring form | existing CSRF/idempotent brief create contract |
| `/content-studio/{uuid}` | detail/editor, content pieces, revisions and local deterministic composer | existing server owner/revision checks |

The Board's five start cards may carry only the allowlisted `kind` query value
to `/content-studio/new`: `caption_hashtag`, `content_ideas`, `hook_script`,
`content_pack` and `storyboard`. They never copy brief text, identifiers,
references, form state, Telegram state or an execution instruction into the
new route.

## Existing read model; no new backend surface

The root board reuses the current owner-scoped reads already hydrated for
Content Studio:

- `GET /api/v1/content-studio/summary`
- `GET /api/v1/content-studio/briefs?...`
- `GET /api/v1/content-studio/events?limit=50`
- `GET /api/v1/content-studio/policy`
- `GET /api/v1/content-studio/references`

The focused `/content-studio/new` route has a deliberately smaller signed
reader: it requests only `policy` and `references`, which are the two inputs
needed to render an authoring form safely. A transient list, summary or
timeline error must not make a healthy create contract appear unavailable.
It clears board data before rendering and still fails closed when either of
those required owner-scoped reads fails.

No database table, migration, API namespace, background worker, provider
adapter, upload flow, job, payment path or bridge read model is added. The
browser renders only the existing bounded owner-scoped projection. The server keeps
account ownership, field redaction, query validation, pagination, CSRF,
idempotency, optimistic revisions and audit handling authoritative.

## Truthful states and recovery

The Board and the focused authoring route observe the existing
`contentStudioReadState` instead of assuming data is ready.

1. **guarded** — signed session or Content Studio capability is unavailable.
   No historic brief, browser substitute, Telegram record or provider result is
   rendered.
2. **loading** — summary, policy, references, brief listing and audit-safe
   events are being fetched for the current signed account. No stale account
   data is preserved.
3. **ready** — the current server projection may be displayed. Full private
   text still requires the existing detail route and server ownership check.
4. **failed** — the projection is cleared. A retry appears only when the
   existing signed refresh capability is available; the page does not replace
   the failed read with Bot data, prompt output or a fake activity feed.

Filtering, paging and refresh reuse the existing ephemeral Content Studio
handlers. Query/filter values remain session-local and do not become URL,
Telegram or browser-storage state.

## Bot parity and execution boundary

The static parity inventory currently has no Bot command/callback mapped to
`/content-studio`. Related Bot content paths remain their own guarded Web
routes (for example Content Prompt Pack, Publish Review Pack and Contextual
Ad Prompt); the Board must not absorb their Telegram callbacks or pending
state.

Content Studio remains Web-native authoring only. It has no Bot bridge,
Telegram identity mutation, provider call, AI output claim, job, Xu ledger,
PayOS order, payment webhook, publish, export, delivery or notification side
effect. The existing local deterministic composer remains explicitly labelled
as draft scaffolding, not AI output.

## Private PWA policy

`/content-studio` and `/api/v1/content-studio` are both explicit private
Service Worker prefixes. They never enter the public shell cache or offline
fallback. This protects summary, activity, reference metadata and brief
projections across sign-out or account switching.

## Focused acceptance checks

- Root board, focused `/new` form and `{uuid}` detail keep their distinct
  responsibilities and canonical paths.
- Only the five allowlisted content kinds can be preselected by a start card;
  a valid card choice wins over any in-memory draft kind from a prior form.
- A view-only session receives explanatory, non-clickable create affordances;
  it is never routed from a live-looking create card into a disabled form.
- Read states are visible and recoverable without stale/private fallback data.
- Recent activity contains only action label, revision and time; not brief
  text, reference values, raw paths, payloads or provider data.
- Mobile controls retain a 44px minimum target, keyboard focus is visible and
  reduced motion removes decorative transforms.
- No Bot, provider, wallet, PayOS, job, webhook, database or API changes are
  included in this UI-only PR.
