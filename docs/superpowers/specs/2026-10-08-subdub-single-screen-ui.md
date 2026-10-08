# SubDub single-screen UI closeout — 2026-10-08

**SPEC_ID:** `SUBDUB-SINGLE-SCREEN-UI-20261008`
**STATUS:** `EXACT_UI_QA_PASS_RELEASE_PENDING`
**BASE_SHA:** `e70175a5f8b4d30bdf99de939b80d2de2e54ee18`
**AUDIT_BASE_SHA:** `13d4a06f2f63217d9a1a682b7df950bacc5a62b2`
**VIDEO CHECKPOINT:** PR #616 is recorded as merged at
`8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952`; this spec does not reopen that
checkpoint or claim the remaining Video family is complete.

## Goal

Make `/subdub` a single, understandable workspace with four clear choices:
original-language subtitles, translated subtitles, dubbing only, and subtitles
plus dubbing. Show only the settings relevant to the selected choice, expose
separate original-audio and dubbed-voice level controls when dubbing is part of
the choice, and reserve one truthful area for the future job report.

Keep the existing blue–teal brand and separate Vietnamese, English, and
Simplified Chinese copy. The processing gate remains authoritative: the current
source intake, price/estimate, and run action stay guarded until the actual
media adapter and price authority are available.

## Baseline findings recorded before implementation

- `renderSubDubHub` currently uses four links with full query navigation; the
  current settings panel is conditionally rendered per query, so changing a
  mode reloads the same route instead of changing the selected mode in place.
- Dubbing currently offers a coarse original-audio choice only; there is no
  separate level control for the original audio and dubbed voice.
- A static six-state guide is placed above an empty result message that says
  “Status: Preparing,” which can be mistaken for a live job.
- `resolveSubDubLocale` accepts only `vi` and `en`; `zh` currently resolves to
  Vietnamese. The Vietnamese / English copy dictionaries have no Chinese
  counterpart.
- Existing HTML contains inline layout styles and no route-scoped visual
  system for the mode selector. The older screenshots in
  `reports/browser_evidence/screenshots/` were captured on 2026-07-10 and are
  historical evidence, not a render of this current source snapshot.
- The four canonical product lanes remain the source contract. Existing server
  routes, actions, engine inputs, pricing, and wallet authority are protected.

## Scope and protected paths

**Allowed:**

- `static/portal/portal.js` — only the SubDub renderer and the isolated
  SubDub-mode / local-volume presentation handlers.
- `static/portal/portal.css` — new `.portal-subdub-*` styles only; preserve the
  existing blue–teal semantic tokens and reduced-motion behavior.
- `tests/subdub-hub-presentation.test.mjs` and this spec/checklist/state record.
- `tests/test_web_subdub_uiux_product_journey_remediation.py` — update only
  the two frozen Vietnamese heading assertions to match the reviewed copy;
  preserve every source/price/voice/run safety assertion.

**Protected:**

- API routes, upload authority, Bot bridge, job lifecycle, pricing, Xu/wallet,
  provider calls, admin trace, and database schema/data.
- Shared navigation, global theme tokens, `portal-motion.js`, and unrelated
  Voice/Music edits already present in the dirty worktree.

## Ordered checklist and acceptance

### S1 — One-screen mode selection

- [x] Show all four choices as accessible controls in the same `/subdub` view.
- [x] Selecting a mode updates the visible panel, selected state, and query
  metadata without a product-route change, page reload, form submission, or
  network request.
- [x] Keep one clear page heading; remove redundant summary/vanity-stat blocks.
- [x] Keep the existing four lane IDs and map them to the existing mode keys.

**Acceptance:** all four choices are reachable by keyboard and touch; exactly
one configuration panel is visible; selected mode and review summary stay in
sync; existing mode query aliases still choose the correct initial mode.

### S2 — Audio settings without fake execution

- [x] In dubbing-only and combined modes, show separate 0–100% presentation
  controls for original audio and dubbed voice with visible live values.
- [x] Keep these controls local to the open view: no `name` attribute, payload,
  persistence, bridge request, or change to engine contracts.
- [x] Explain naturally that the values are not applied to a real output while
  media processing remains unavailable.
- [x] Keep voice/source controls and the run CTA guarded; do not add fake upload,
  estimate, job, charge, or output behavior.

**Acceptance:** sliders update only their visible values; no task/API/form
request is produced; source-only modes do not show dubbing-only controls.

### S3 — Honest report and locale presentation

- [x] Replace the static status-card legend plus “Preparing” empty status with a
  concise no-task report area. Only a future verified receipt may display a
  request ID, stage state, or downloadable result.
- [x] Fully render the SubDub screen in `vi`, `en`, and `zh`; no Vietnamese
  fallback in an English or Chinese view. Keep technical formats and proper
  nouns (SRT, VTT, AI, SubDub) unchanged where appropriate.
- [x] Preserve responsive blue–teal styles; text contrast ≥ 4.5:1, control
  boundary ≥ 3:1, touch targets ≥ 44px, and no horizontal overflow at 360px.

**Acceptance:** renderer matrix passes four modes × three locales; guarded and
empty states are explicit; no route/engine/wallet/provider files or effects
change.

## Verification plan

- Run the new dependency-free Node renderer contract and the existing SubDub
  source-contract tests where the test runner is available.
- Run `node --check` for `static/portal/portal.js` and `git diff --check`.
- Use local Playwright against the rendered SubDub surface for desktop/mobile
  layout, keyboard selection, volume-value feedback, current URL, console, and
  request count. No live media submission.
- Capture before/after screenshots outside the repository and record exact
  viewport, locale, source SHA, and results here.

## Safety ledger

`PROVIDER_CALLS=0` · `WALLET_MUTATIONS=0` · `PRODUCTION_DATA_MUTATIONS=0` ·
`ROUTE_ENGINE_CHANGES=0` · `DEPLOY=NO`.

## Result

### Verified local checkpoint — 2026-10-08

Release-source candidate `40b3ce7` repeated the full template/handler matrix:
12/12 configurations and 48 selections passed; minimum text 5.23:1, boundary
3.51:1, target 44px. Exact snapshot evidence is at
`../../qa/subdub-exact-40b3ce7/browser-review.json`. Official browser proof
for the same snapshot is at `../../qa/subdub-release-40b3ce7/reports/browser_evidence/`.
The current release branch is already based on current `origin/main`
`e70175a5f8b4d30bdf99de939b80d2de2e54ee18`; the SubDub change is isolated from
the Voice/Music/Video product blocks marked CLOSED/LOCKED. This does not reopen
those product blocks.

- Four in-page choices keep exactly one settings panel visible. Enter and
  click/touch keep selected state, review summary and URL mode aligned while
  preserving the locale. Four legacy query aliases also pass the renderer test.
- Subtitle, voice and combined settings use vertical layout. Radio format
  groups are isolated per mode, so switching modes preserves each selection.
  Dubbing modes expose independent local original/voice levels with keyboard
  feedback (100% → 99%). No request or Portal action event is emitted.
- Removed the duplicated vanity statistics, false “Preparing” report and
  success checkmark from the empty report. Unknown wallet data displays “—”
  rather than an invented zero; the underlying wallet authority is unchanged.
- Hero descriptions and all fixed SubDub content render in VI/EN/ZH. Labels,
  headings and control edges were corrected from measured contrast failures.
  Repeated implementation jargon and safety tags were replaced with concise
  availability explanations.
- Renderer tests **9/9**, combined Voice/Music/SubDub Node regression **61/61**,
  existing Python UI contract **9/9**; JavaScript syntax and diff checks passed.
  The existing Python contract changed only two frozen heading expectations.
- Actual Portal template, complete `portal.js`, i18n, theme and motion ran at an
  intercepted QA origin. VI/EN/ZH × light/dark × 1440×900/360×900 = **12 cases**;
  all four modes exercised in each = **48 interaction checks**. No horizontal
  overflow, duplicate IDs, runtime errors, failed resources, post-load requests
  or action events. Text minimum **5.23:1**, control-boundary minimum **3.51:1**,
  effective target height minimum **44px**. Source hashes remained stable.
- **48 screenshots + JSON evidence:**
  `../../qa/20261007-video-uiux/subdub-shell-verified-20261008/`.
  Reproducible runner: `../../qa/20261007-video-uiux/subdub-review.mjs`.
  The earlier incomplete-wrapper screenshots are superseded and are not used
  for acceptance. Browser plugin was unavailable; regular Playwright was used.

### Exact current-branch recheck — 2026-10-08

- Current branch `fix/subdub-ui-closeout-20261008`, exact HEAD
  `e4070e3bf6710be1e5388c12e20800aae0ee5ea3`, is based on current
  `origin/main` `e70175a5f8b4d30bdf99de939b80d2de2e54ee18`.
- Re-ran `node --test tests/subdub-hub-presentation.test.mjs`: **9 passed,
  0 failed**. Re-ran the Python SubDub UI contract using the isolated QA venv
  with cache writing disabled: **9 passed, 0 failed**. `node --check
  static/portal/portal.js` and `git diff --check` both exited 0.
- Rechecked the exact-source browser JSON: **12/12** locale × theme × viewport
  cases and **48/48** mode interactions; runtime errors, failed requests,
  post-load requests, action events, duplicate IDs and horizontal overflow are
  all `0`. Text contrast is **5.23:1**, control boundary **3.61:1**, and
  minimum touch target **44px**. The six UI source hashes are stable.
- Exact evidence: `../../qa/qa/subdub-exact-e4070e3/browser-review.json`;
  48 screenshots remain outside the repository. This is local rendered QA only;
  it does not prove signed-session behavior, real media execution, deployment,
  or production live behavior.

### Release and remaining scope

- [x] Local code commit and exact-source QA complete.
- [ ] Push/PR/CI/merge and production browser verification remain pending.
- [ ] Production deployment requires its own explicit Owner authorization.
- [ ] Shared navigation locale and floating controls, followed by the global
  motion gate, remain open in the parent UI checklist.

This proves the local SubDub presentation checkpoint only. `integration.js`
was excluded from the isolated QA fixture; no server, database, signed-account
authority, upload, provider, quote, job or real output was exercised. Actual
execution remains guarded and is owned by the route/engine workstream. Parent
goal stays ACTIVE. Close the Voice, Music and SubDub release gates sequentially
before starting other product UI; remaining Video and the final motion gate
keep their existing order.
