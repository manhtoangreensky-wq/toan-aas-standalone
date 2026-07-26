# Delivery Workspace Navigation UX Design

## Goal

Make the signed delivery area feel like one deliberate application workspace
by giving Job Center, canonical Assets, and the Web-owned Asset Vault a shared
navigation layer. The navigation must improve orientation without blurring
the boundary between a Bot-validated delivery and a private file stored by the
Web application.

## Chosen approach

Place a compact horizontal **Delivery** strip directly below each page hero on
these existing routes:

- `/jobs` — **Job Center**
- `/assets` — **Tài sản**
- `/asset-vault` — **Asset Vault**

The strip uses normal anchors, exact `aria-current="page"` state, and the
existing dark-slate/teal application tokens. `/jobs/{id}` is part of the Job
Center journey and keeps **Job Center** active; no other dynamic route is
invented.

This is preferred over a new Delivery landing page or sidebar because the
global app shell already owns primary navigation, while customers need an
immediate, deep-linkable way to move between status, validated canonical
asset metadata, and their independently owned private references.

## Interaction and responsive behavior

- Every destination is a plain same-origin anchor. Back/Forward, direct URLs,
  signed route gates, and ownership checks remain server controlled.
- Desktop presents one aligned compact row below the page hero.
- At narrow widths, only the strip scrolls horizontally; the document itself
  must not gain horizontal overflow. Each link has at least a 44px target,
  visible focus state, scroll snap, and reduced-motion coverage.
- The active item is determined from the current route only. A job detail
  displays **Job Center** as current because it is a detail of `/jobs`, not a
  fourth independent delivery surface.

## Authority and safety boundary

The navigator is route-only. It does not create a job, poll a provider,
refresh data, upload a file, issue a download, create a ticket, retry or
refund a job, calculate Xu, create/finalize PayOS, or expose a raw Bot
identifier, delivery URL, provider response, or ledger data.

The labels intentionally mean different things:

- **Job Center** is canonical job metadata scoped to the signed identity.
- **Tài sản** is canonical, owner-scoped asset metadata. A download remains
  guarded until the existing private delivery contract approves it.
- **Asset Vault** is Web-owned private reference storage. A Vault file is not
  an output, job, delivery, provider input, or payment artifact.

Existing route-level signed-session, CSRF, ownership, validation, and delivery
checks are unchanged and rerun at each destination.

## Verification

- A static contract proves exactly three approved anchors, one exact active
  condition, correct `/jobs/{id}` normalization, absence of actions/network/
  payment/provider/ledger tokens, and presence on Jobs, Job Detail, Assets,
  and Asset Vault renderers.
- CSS contract proves tokenized containment, 44px controls, internal scroll,
  focus styling, narrow-screen handling, and reduced-motion handling.
- Existing delivery and Asset Vault contracts remain green.
- Browser QA follows `/jobs` → `/assets` → `/asset-vault` and `/jobs/{id}`
  with a local signed account, then checks a 375px viewport for a scrollable
  strip, 44px targets, no page overflow, correct active state, and no console
  warnings/errors. Provider, payment, Bot, and production delivery remain
  disabled.
