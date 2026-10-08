# Voice flow-state presentation — 2026-10-08

Base: `13d4a06f2f63217d9a1a682b7df950bacc5a62b2`.
Owner scope: UI/copy/layout only; API, route engine, provider, wallet and billing
authority stay unchanged. Continue this slice before Music.

## Contract

Allowed: `static/portal/portal.js`, `portal-i18n.js`, `portal-theme.css`,
targeted renderer tests and QA-only fixture runner; state/spec/checklist.
Protected: backend, `integration.js`, field/action/receipt semantics, paid calls,
wallet/payment code, Video checkpoint and other feature renderers.

## Ordered checks

- [x] Reproduce draft/estimate/confirm/tracking/error output in VI/EN/ZH.
- [x] Voice-only localized status/quote/detail UI; no internal cost/provider
  price/source/version fields. 0 Xu is a known value; missing price is unknown.
- [x] Preserve all existing confirm gates: authenticated/capability/bridge,
  fresh fingerprint and opaque receipt; no direct confirm from draft/stale.
- [x] Preserve safe tracking: explicit ID + same feature + same status only;
  no inferred job, player or download from reported completion.
- [x] Render draft, quote, awaiting runtime, queued, processing, completed,
  failed/no-charge/error/cancelled/refunded with truthful next steps.
- [x] Direct renderer tests and actual QA browser flow-state matrix, keyboard,
  light/dark contrast, mobile layout, no external/production POST.
- [x] Update this checklist and durable state with the verified TTS checkpoint.
- [ ] Voice family/release verification and CI remain open; TTS fixtures do
  not prove a real estimate, job, audio output, charge or live delivery.

## TTS verification — 2026-10-08

### Review before release

- Resumed-draft coverage exposed an empty save-new label in VI/EN/ZH. Added
  `voiceUi.draft.saveNew` to the Voice catalogue (not Video); the existing
  update/save actions and draft ID semantics are preserved.
- Price coverage exposed ambiguous `cost_xu` fallback. Only the public
  `estimated_xu`/`quote_xu` fields are displayed as price; internal cost does not
  suppress a valid public quote or become a sale price when the quote is absent.
- Both defects were reproduced RED in all three locales, then fixed GREEN.
  Six Voice renderer suites now pass **110/110**. Exact release-tree/CI/browser
  verification is still required; prior browser images do not prove these new
  edge cases were deployed.

- Direct production-renderer contract: 45/45 passed across VI/EN/ZH. Covers
  quote/zero/unknown, localized disabled tooltip, runtime-ready guard, fresh
  receipt/capability gates, matching tracking, result/error states and no fake
  audio or provider-cost fields.
- Browser flow matrix: 72/72 cases on `/voice/tts` (VI/EN/ZH × light/dark ×
  1440/375; quote, stale, processing, completed, failed-no-charge, error).
  Boundary matrix: 36/36 cases (zero, unknown and draft). Source hashes stable;
  zero overflow and route runtime errors.
- Minimum text contrast: 5.473:1 light and 4.515:1 dark. Minimum form control
  border contrast: 3.399:1. Confirm action is present only for a fresh quote
  with a visible price (including 0 Xu); stale/unknown/error/result states do
  not expose it. Tracking links require the matching task reference.
- Keyboard expand/collapse and collapsed prior form pass. No business POST,
  provider request or wallet mutation was made. Browser fixtures project UI
  state only and do not grant server capability or confirm an actual job.
- Evidence: `../../../../../qa/20261007-video-uiux/voice-tts-flow-final-20261008/`
  and `../../../../../qa/20261007-video-uiux/voice-tts-boundary-final-20261008/`.
- Known QA setup warning remains: `ViewTransition` invalid-state during
  login/setup. Four background auth GETs remained pending at matrix close; the
  browser report does not prove those reads completed. Global motion and
  shared-shell locale remain separate open work.

Fixtures represent presentation states only. They do not authorize or prove a
real quote, job, provider, output, charge, refund or ownership decision.
