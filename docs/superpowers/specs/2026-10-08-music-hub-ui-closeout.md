# Music hub UI closeout — 2026-10-08

Status: `MUSIC_RELEASE_PREPARATION`.
Release BASE: `e405cbee28f0687f528eab7d66a71ef1623125f4`.
Branch: `fix/music-ui-closeout-20261008`.
Voice PR #617 and selected Video PR #616 product source/release are CLOSED/
LOCKED. This checkpoint must not edit their renderer/catalogue/product CSS.

## Goal

Make the existing `/music` landing screen easy to understand and scan in
Vietnamese, English, and Simplified Chinese. Lead with the actual music-creation
choices, clearly show which ones are not available, and present the existing
working library tools without repeated cards or unsupported quality/licensing
claims.

## Baseline and defects

- Baseline QA: 12/12 cases completed on `/music` across VI/EN/ZH, light/dark,
  1440×900 and 375×812. The route had no horizontal overflow or route runtime
  error; source snapshot was `13d4a06f2f63217d9a1a682b7df950bacc5a62b2`.
- The English screen contains Vietnamese fixed copy; the Vietnamese screen
  mixes product copy with English terms that are not product names.
- “Stereo 320k”, studio-quality, royalty-free, and commercial-rights claims are
  hardcoded without a reviewed source. Remove them; do not replace them with
  other performance, quality, copyright, or licensing promises.
- The first screen spends too much space on the hero and three unsupported
  metrics. A three-card “quick start” repeats the same destinations shown in
  the tool catalogue and delays the music-creation choices on mobile.
- The canonical blue–teal theme is already the right brand direction; preserve
  its semantic tokens and the existing light/dark behavior.

## Implementation contract

Allowed files:

- `static/portal/portal.js`
- `copyfast_pages.py` — only the fixed `/music` HTML title translations;
  keep every route registration and all Voice/Video title entries unchanged.
- `static/portal/portal-i18n.js`
- `static/portal/portal-theme.css` only if a measured Music-only layout fix is
  required; do not change shared theme tokens.
- `tests/music-hub-presentation.test.mjs`
- `scripts/ci/run_browser_verification.py` — Music selectors only, checking
  the actual first creation card for content/visibility/behavior/focus; keep
  Voice and other hub selectors and fail-closed assertions intact.
- Web-only source provenance and measured Tester case metadata for release.
- This spec, `reports/audit/P0-WEB-ERP-MASTER-CHECKLIST.md`, and the matching
  `.agents/state/WEBAPP-MUSIC-HUB-UI-20261008.yaml` checkpoint.

Required behavior:

1. Localize the `/music` page title, description, section labels, group names,
   tool names, descriptions, state text, and actions in VI/EN/ZH. English must
   not contain Vietnamese; Vietnamese must not contain mixed English prose.
   Keep accepted names/acronyms such as TOAN AAS, AI, MP3, and M4A only where
   needed.
2. Put the three existing AI creation destinations first and show their real
   guarded/unavailable state. Keep the three existing Web library/audio-file
   destinations after them as available. Preserve the exact six route paths;
   do not enable a generation action.
3. Remove the duplicate quick-start card section and unsupported quality,
   format, copyright, and commercial-use claims. The only numeric summary may
   be the count of unique, existing destinations, calculated from the rendered
   links.
4. Use short, action-oriented copy; keep the current blue–teal light/dark theme,
   page shell, heading hierarchy, keyboard navigation, and responsive card
   styling. Do not add decorative animation or change global motion behavior.
5. Preserve all server routes, fields, actions, bridge/engine boundaries and
   data permissions. Do not create audio, a player, a job, an estimate, a
   provider request, a wallet action, or any production record.

## Ordered acceptance checklist

- [x] Read the current rendered source and 12-case baseline; save screenshots
  and JSON at `../../qa/20261007-video-uiux/music-hub-audit-20261008/`.
- [x] Add direct production-renderer tests for VI/EN/ZH, exact route set,
  creation-first order, truthful guarded labels, no duplicated cards, and no
  unsubstantiated claims; the six initial assertions and one scoped contrast
  guard pass.
- [x] Implement the smallest route-scoped renderer/catalogue changes. Shared
  `renderMediaHubPage` defaults for Image must remain unchanged.
- [x] Run Music renderer tests, all six Voice UI test files, relevant existing
  Music safety contracts, JavaScript syntax checks, and `git diff --check`.
- [x] Run a fresh browser matrix: 12/12 locale × theme × desktop/mobile cases;
  verify 375×812 and 1440×900, no overflow/route errors, content order, links
  and unchanged destinations. Direct contrast sampling covers 32 Music text
  elements per theme: minimum 4.635:1 light and 4.812:1 dark, none below 4.5:1.
  A click on the guarded `/music/create` link reached the route; no form submit.
- [x] Review screenshots and diff; update this spec, master checklist and state.
  Shared-shell locale, the existing ViewTransition setup warning, and global
  motion remain separate open work. Music execution/provider behavior remains
  explicitly outside this checkpoint.

## Verification results — 2026-10-08

### Release review gates

- [ ] Verify fresh candidate on the Voice release BASE and preserve SubDub
  worktree changes outside this commit.
- [x] Identify the Music primary card and align Music-only CI selectors;
  direct VI/EN/ZH assertions reproduced RED then pass. Keyboard/touch browser
  proof still requires the fresh exact-candidate matrix.
- [x] Assert the closed Voice/Video product source is unchanged: 43 functions,
  3 catalogues and product CSS line projection match locked merge BASE.
- [ ] Refresh Web provenance and case metadata after narrow staging; Ubuntu
  Web CI must pass before merge and separate exact-SHA deployment.

- Node: Music presentation 7/7; combined Music + six Voice UI suites 117/117.
- JavaScript syntax and `git diff --check`: pass.
- Existing Music Python contracts: 23 passed; one failure is the unchanged
  baseline test `test_library_routes_do_not_fall_back_to_generic_assets_or_audio_execution`,
  whose helper requires a literal legacy `/assets` hydration branch. Both
  `integration.js` and that test file are byte-identical to `origin/main`; no
  engine, API or integration source was changed in this checkpoint.
- Browser: 12/12 complete, stable source hashes, zero missing headings,
  horizontal overflow, route runtime errors or blocked requests. The setup
  screen logged the already-known ViewTransition invalid-state warning; several
  background read-only auth/catalog GETs remained pending at close.
- Evidence: `../../qa/20261007-video-uiux/music-hub-ui-closeout-20261008/`
  (12 screenshots + `browser-review.json`). The page-level copy is localized;
  screenshots also expose mixed Vietnamese navigation in the shared shell on
  English/Chinese views, which remains open outside this Music-only slice.
- Safety: `PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.
  Route checks used the isolated local QA account. No audio, estimate, job,
  provider request, form submission or production record was created.
- Delivery: local worktree only; not committed, pushed, merged, deployed or
  claimed live.

## Verification commands

- `node --test tests/music-hub-presentation.test.mjs` → expected: all focused
  renderer assertions pass.
- `node --check static/portal/portal.js; node --check static/portal/portal-i18n.js`
  → expected: no syntax output/errors.
- Browser runner: use the already configured QA runner for this checkout;
  expected: exactly 12 complete cases, zero route runtime errors and zero
  horizontal overflow. The Browser plugin is not present in this session, so
  Playwright fallback must be recorded with its exact command and evidence.

`PROVIDER_CALLS=0 WALLET_MUTATIONS=0 PRODUCTION_DATA_MUTATIONS=0`.
No claim in this spec means the guarded AI generation routes work end to end.
