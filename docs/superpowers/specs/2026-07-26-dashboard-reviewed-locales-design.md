# TOAN AAS Dashboard Reviewed Locale Design

## Purpose

Make the signed `/dashboard` command center consistently understandable in
Vietnamese, English and Simplified Chinese while preserving the existing
teal–cyan workspace design and all data/authority boundaries.

## Scope for this slice

- Translate the Dashboard core presentation copy: workspace summary, recent
  Project/Draft cards, first-session guide and account lane, plus the visible
  section headings that lead into canonical work, action center and launchpad.
- Reuse the existing Portal i18n bundle and `safeText` boundary. Add a
  dedicated `dashboard.*` catalogue with exactly equal `vi`, `en` and `zh`
  keys.
- Render the active reviewed display locale only. Customer data, canonical
  metadata, provider/job state, project names and user-written content remain
  byte-for-byte server/customer values.
- Keep the present command-center information architecture, routes, signed
  hydration, failure semantics, PWA private-path rules and mobile layout.

## Explicit non-goals

- No Bot source, Core Bridge contract, PayOS/wallet ledger, provider call,
  webhook, job state, delivery or authentication change.
- No translation of prompts, briefs, documents, project names or canonical
  responses in the browser.
- No fake counts, fake activity, fake success, fake delivery or new charts.
- No broad UI rewrite, new framework or route change.
- Detailed canonical table labels, action-card descriptions and individual
  Studio catalog copy remain a following, separately reviewable locale slice.

## Design and accessibility

- The dashboard follows the accepted dark ink-blue workspace concept at
  `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-167f60fc-c499-4a3f-a730-f88c7c120dae.png`
  and the `/dashboard` page override.
- Fixed labels remain concise, clear and task-oriented in all three languages.
  Localized wording must not exaggerate a guarded capability into availability.
- Existing Portal SVG icons, keyboard order, 44px mobile controls and
  reduced-motion rules remain intact.

## Acceptance criteria

- Every `dashboard.*` key is non-empty and identical across reviewed locale
  keysets.
- The Dashboard renderer has no hard-coded fixed Vietnamese/English display
  copy in the changed command-center functions; fixed text reads through the
  reviewed catalogue and `safeText`.
- Locale selection is presentation-only: no local persistence, provider
  request, billing/wallet mutation, canonical write or private-cache change is
  introduced.
- Existing Dashboard safety, canonical-read and PWA contracts remain green.
