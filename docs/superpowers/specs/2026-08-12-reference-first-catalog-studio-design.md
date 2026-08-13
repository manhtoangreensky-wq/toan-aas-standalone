# Reference-first Feature Catalog and Studio — Design

## Owner direction

The supplied product reference is the fast structural model for this slice.
TOAN AAS may closely reproduce the useful interaction hierarchy: a compact
application shell, a searchable tool directory, a decisive workflow rail,
clear page rhythm, responsive density and restrained motion. It must not copy
the reference's source code, brand, logo, imagery, copywriting, metrics,
testimonials, data, API contracts or proprietary workflow rules.

The existing TOAN AAS Aura system remains authoritative: teal/cyan, light,
dark and system themes; Vietnamese, English and Simplified Chinese; customer
workspace separate from `/admin`.

## Problem

The customer app already has a registry-driven `/features` directory and a
route-only `/studio` page. The directory is structurally sound, but the Studio
is a legacy six-card sequence with Vietnamese-only fixed copy. It does not
make the first next step, later review, jobs or delivered assets scan as one
professional Web workflow.

## Reference-first implementation

### Feature directory

`/features` keeps its server-issued registry cards, route records and
readiness labels. This slice only refines the presentation shell already in
place: search first, intent groups second, then a clear continuation into the
Studio. The browser never manufactures cards, routes, prices, provider status
or readiness values.

### Media Studio

`/studio` becomes a truthful working rail with six fixed route links:

1. Discover — `/features`
2. Brief — `/content/storyboard`
3. Plan — `/video/product`
4. Review — `/approvals`
5. Jobs — `/jobs`
6. Assets — `/assets`

The rail is navigation only. It does not create a project, call a provider,
make a quote, confirm a workflow, create a job, claim an output or alter a
wallet/payment record. Each destination retains its own signed-session,
ownership and execution boundaries.

### Fixed copy and accessibility

All fixed Studio labels, descriptions, buttons and document metadata are
placed in one `mediaStudio.*` namespace with equal `vi`, `en` and `zh`
keysets. Dynamic records remain server data and are not translated in the
browser. The rail has a labelled section, semantic links, visible keyboard
focus and a single obvious primary continuation.

### Visual and motion system

The implementation uses the existing `--portal-*` semantic tokens only. It
uses a professional application rail rather than a landing-page card wall:
an oriented introduction, a connected step grid on desktop and a calm stacked
flow on smaller screens. Optional reveal is limited to opacity/transform over
the shared 150–220ms grammar. Focus reveals content immediately; no observer
or reduced-motion environment can hide content.

## Out of scope

Bot source, `bot.py`, Core Bridge, providers, routing engines, job execution,
wallet, PayOS, pricing, credentials, ENV, database changes, deployment and
any live/provider/payment test remain untouched.

## Acceptance criteria

1. `/features` remains registry-led and truthful.
2. `/studio` presents the six existing navigation destinations as one clear
   route-only flow with no fake job/provider/payment/output claim.
3. All fixed Studio chrome and page metadata have reviewed VI/EN/ZH keys.
4. Studio participates in the existing workspace motion lifecycle and its
   reduced-motion cleanup.
5. CSS is token-only, responsive, keyboard-safe and does not create a second
   palette.
6. Static contracts, targeted regression tests, Node syntax checks, diff
   check and browser visual QA provide evidence before any merge claim.
