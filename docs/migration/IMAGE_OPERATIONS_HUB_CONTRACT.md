# Image Operations Hub — Web-native projection contract

## Purpose

`/image-hub` is the app-first Image Operations Board for a signed Web
account. It is a compact visual projection of the existing Image Creative
Studio authority: artboards, creative directions, revisions, policy and
owner-scoped project/image-asset references. It is **not** a second image
engine or persistence boundary.

The compatible `/image-studio` family remains the full Image Creative Studio
editor. A customer may choose either visual route family; both resolve to the
same server-authorized artboard UUID and existing Web authority.

## Localization note

This module keeps its concise Vietnamese workspace copy while the planned
portal locale pass expands the professional UI consistently across Vietnamese,
English and Chinese. The Image Hub does not create a route-specific translation
store, browser preference or fallback; presentation copy will move through the
shared portal locale system in that dedicated follow-up.

| Surface | Authority | Never introduced by this projection |
| --- | --- | --- |
| `/image-hub`, `/image-hub/new`, `/image-hub/{artboard_id}` | Portal route, renderer and hydration layer | `image_hub` database table, API namespace, browser-storage namespace, provider adapter, image catalog, ledger or job state |
| `/api/v1/image-studio/*` | Existing standalone Web Image Creative Studio | Bot callback/state replay, Telegram identity, provider request, wallet/Xu or PayOS mutation |
| `/image-studio/*` | Existing compatible Image Studio editor | Forced redirect away from the customer-selected visual route |
| `/api/v1/image-operations/*` and `/image/*` operation pages | Existing independent image-operation authority | Implicit processing, hidden upload, automatic asset handoff or simulated output from the Hub |

## Route and existing read model

```text
/image-hub                         -> existing summary, policy, artboard-list,
                                      event and owner-scoped reference reads
/image-hub/new                     -> existing Image Studio artboard-create flow
/image-hub/{artboard_id}           -> existing signed artboard detail, policy,
                                      references, revision history and estimate reads
```

All Hub hydration and mutation calls remain in the existing
`/api/v1/image-studio/*` namespace. In particular, the projection may use
the already-authoritative `summary`, `policy`, `artboards`,
`artboards/{artboard_id}`, `artboards/{artboard_id}/estimate`, `events`,
`references/projects`, and `references/image-assets` endpoints, plus their
existing artboard/direction lifecycle mutations. It must not call or create
`/api/v1/image-hub/*`.

After a create or duplicate-like action, the portal keeps the selected visual
family: an Image Hub action opens `/image-hub/{artboard_id}`; an Image Studio
action stays on `/image-studio/{artboard_id}`. The alias changes presentation,
not the authoritative model, request payload, revision policy, account
boundary or result semantics.

## Board safety and explicit operation links

The board is a planning and review surface. It may render only server-sanitized,
owner-scoped metadata needed to understand an artboard, its directions, state,
revision and opaque references. It never turns a reference into a browser
authority or an image-processing result.

The board provides independent, explicit next-step links to existing Image
Operations surfaces, such as `/image/resize`, `/image/edit`,
`/image/brand-overlay`, `/image/storyboard-grid` and `/image/history`. A link
is navigation only. It does not prefill, submit, transfer or persist an
artboard, project, asset, account or operation identifier through a URL/query,
fragment, browser storage, hidden form field or background request.

The Hub must not add any of the following:

- image bytes, Blob/object URLs, raw storage paths, filenames, signed download
  URLs, inline previews, provider/catalog/model calls or a browser-side image
  engine;
- an automatic image-operation invocation, file upload, output import or
  cross-surface selection;
- a provider/job/payment/wallet completion claim, generated output, fake
  thumbnail, delivery state or charge/refund side effect.

Actual image transformations, asset validation, output delivery and private
downloads remain the responsibility of their existing Image Operations and
Asset Vault routes. A fresh server-authorized operation read is required there;
the Hub is never a substitute for it.

## Security, revision and lifecycle guarantees

- Existing signed-session checks (`require_account`) remain mandatory for every
  read; server-side account ownership is re-evaluated for every artboard,
  direction, project and image-asset reference.
- Existing CSRF validation (`require_csrf`) remains mandatory for every
  mutation. A UUID is an opaque locator, never proof of ownership or authority.
- Existing Image Studio compare-and-swap rules remain canonical: edits and
  lifecycle changes carry `expected_revision`, conflicting revisions fail
  closed, and the client rehydrates the authoritative detail before another
  edit.
- Existing idempotency keys, audit events, bounded version history and input
  policy controls remain intact. The projection neither removes nor reimplements
  them.
- A failed signed read, policy guard, ownership check or revision check cannot
  be replaced with stale `/image/*` operation history, a cached artboard or
  browser-supplied data.
- `/image-hub` is a private PWA route. It must be in the service-worker private
  path policy and excluded from the public shell cache and offline navigation
  fallback, so an account's artboard metadata cannot reappear after sign-out or
  account switching.

## Non-goals

This module does not modify Bot code or reproduce Bot state. It does not add
an image provider integration, Key4U/model invocation, webhook, worker,
background retry, storage authority, image ledger, PayOS/wallet/Xu logic,
admin write path, new database migration, new API router or new feature flag.
It also does not alter the established Image Studio or Image Operations API
contracts.

## Focused acceptance checks

- List, new and UUID detail deep links render through the normal signed portal
  shell and preserve the selected Image Hub visual route after authoring
  actions.
- Every Hub read and write remains an existing Image Studio API call; no Image
  Hub API, persistence layer or browser authority exists.
- The full `/image-studio` editor and independent `/image/*` operation routes
  remain functional and are not redirected or silently coupled.
- The renderer contains no raw image path/URL, Blob/object URL, provider call,
  catalog/model selector, image-processing request, query handoff, browser
  persistence or fake output.
- PWA policy treats `/image-hub/*` as private, and an owner-scoped, CSRF and
  revision-conflict failure leaves the board guarded rather than showing stale
  data.
