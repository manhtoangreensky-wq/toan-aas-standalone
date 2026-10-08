# Voice UI closeout — 2026-10-07

Owner order: Voice → Music → SubDub → other features → unfinished Video.
Base main: `8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952` after Video PR #616.

## Voice release checkpoint — 2026-10-08

PR #617 is merged and deployed at
`e405cbee28f0687f528eab7d66a71ef1623125f4`.
PR CI `37724197462` and main CI `37724519640` both succeeded;
deploy `37724809429` succeeded. SSH readback confirms that exact SHA,
tracked diff 0, Web and nginx active. Production JS/i18n/theme bytes match
immutable Git blobs 3/3. Anonymous 1440×900/375×900 entry renders the login
form without overflow or page errors. Authenticated production Voice UI is
still open; no real audio/quote/job/provider/charge claim.

Backup source:
`/opt/toanaas/webapp/delete/deploy-e405cbee28f0687f528eab7d66a71ef1623125f4-20261008035332`.
Readback: `../../qa/20261007-video-uiux/voice-production-e405cbe/readback.json`.
Compare deployment bytes to Git blobs rather than Windows checkout bytes,
which can contain CRLF. The mobile login deliberately hides the desktop hero;
test the actual visible auth card instead of requiring the first h1 to show.

## Contract and historical release checks

## Release gate result — 2026-10-08

- Voice source snapshot `b7628a8c1457f9c8c4fef294dc66368aa01dc2a3`:
  compile/JS syntax and 110 renderer tests pass.
- Official browser runner on this snapshot: 18 page captures, all 6 hubs
  visible, primary links checked, 6/6 keyboard-focus checks, 4/4 deterministic
  free tools, light/dark persistence and no first-paint theme flicker. Runtime
  assertions **26/26** pass. QA server/Chrome were shut down by the runner.
- Bounded Windows suite completed: **387 passed, 2 failed**. One new failure
  was stale Tester case-source line/byte/hash metadata after VUI additions;
  refresh measured 116 lines, 32264 bytes and portable hash. Target retest and
  CI are required. The other is the unchanged POSIX temporary-file mode test
  (Windows reports 0666; test expects 0600); keep the assertion intact and use
  the repository's Ubuntu CI as the release gate.
- Generated browser evidence is retained in
  `../../qa/voice-ui-verify-b7628a8/reports/browser_evidence/`.
  This is isolated QA evidence, not production live acceptance. No paid
  provider, wallet, engine, ENV or production-data action.
- [x] Publish one Voice PR; Ubuntu CI passed 389 contracts + 26 runtime
  assertions and 18 captures before merge/deploy. See the release checkpoint.

Release verification also covers the existing CI runner's Voice DOM selectors
and Web-only migration provenance JSON. Candidate `cddf617` reproduced two
gate failures: Composer additions lacked the page ancestor required by the
theme contract; CI still searched for the old primary Studio shortcut.
Corrective changes scope Composer CSS under its actual page and target the
explicit TTS hub link for content/focus/behavior checks. Guarded metadata is
retained on speech/delivery cards. No gate is disabled or given a vacuous pass.
The Web provenance refresh uses only the clean Voice Git snapshot; Bot records
are preserved. A fresh exact-candidate gate run is required after these fixes.

Review the real signed-in `/voice`, `/voice/tts`, `/voice/saved`, `/voice/clone`,
`/voice/preview`, `/voice/outputs`, `/voice-studio` and direction composer.
Keep existing action IDs, engine guards, field names, values and numeric limits.
The current TTS bridge supports `default_voice_gender`, speed and 0–200
`volume_percent`; the old audit's missing-volume note is superseded.

Use current server contracts to distinguish speech generation, saved-voice
selection, voice-profile planning and audio delivery. Preserve real progress /
quote / confirmation controls where available; do not replace them with draft
actions. Remove only proven contradictory demo panels and technical UI copy.

## Ordered checklist

- [x] Real baseline render: VI, light/dark, desktop/mobile for the eight routes
  (`voice-current-before`, 32 cases; retained source hashes).
- [x] Voice hub: compact navigation, unique destinations, complete VI/EN/ZH
  (`voice-core-after`, 72-case core matrix; seven unique hub destinations).
- [x] TTS `/voice/tts`: content → voice → speed → volume, vertical inputs,
  visible primary action, localized price/status and truthful quote/confirmation
  states. See the 2026-10-08 TTS flow-state evidence below.
- [x] Saved voice `/voice/saved`: keep the ready-profile filter and form flow;
  quote/progress/result states now have route-specific browser evidence below.
- [x] Clone `/voice/clone`: supported consent/sample/name sequence, clear
  capability availability and disabled sample upload when not authorized.
- [x] Preview/output: genuine status/delivery presentation without fabricated
  audio; preserve ownership and access boundaries.
- [x] Voice Studio/composer: separate metadata/text planning from speech
  creation; localized list/detail/cue sheet/composer and preserved private
  controls. Evidence is recorded in the Studio, detail and Composer checkpoints.
- [x] Voice route matrices: VI/EN/ZH × light/dark × desktop/mobile, keyboard,
  text/control contrast, overflow and screenshots are recorded by route family.
- [x] Source contract/syntax checks and completion evidence are recorded below.
  Shared shell language purity and whole-site motion remain open separately.

Scope: Voice presentation and fixed feedback text only. Paid provider calls,
production business actions, API/engine/wallet/ENV changes remain zero.
Do not reuse the older dirty UI worktree as the engine/runtime authority.

Status: `VOICE_PRESENTATION_VERIFIED_LOCAL_RELEASE_CI_PENDING`.

## Initial real-render findings

32 route/theme/viewport cases have been captured. The Voice hub has ten links
for seven unique destinations, mixed technical copy, and decorative quality
metrics before useful choices. TTS/saved/clone forms and libraries have mixed
VI/EN text and need vertical, readable task presentation.

`/voice-studio` also contains the simulated TTS panel inline in
`renderVoiceStudio`: invented named actors, sample MP3,
“NEURAL VOICE ENGINE SẴN SÀNG” and a `-5 Xu` action. It contradicts the genuine
private metadata contract and pushes the real form to y=1926px on mobile.
Remove only that inline sample panel, preserving the actual
Voice Studio forms, consent, capabilities and server actions. Runtime result
evidence is not fabricated; speech generation remains in the real TTS route.

The initial workbench-helper test did not cover the inline panel and was
corrected before implementation. The real `renderVoiceStudio` regression then
failed 2/2 on the false TTS claims, and passed 2/2 after the inline removal.

## Core-route checkpoint

The current core Voice matrix rendered 72 cases (six routes × VI/EN/ZH ×
light/dark × desktop/mobile). It preserves current TTS gender/speed/volume
fields and the 0–200 range; clone fields are consent/sample/name and file
upload stays disabled when the server has not granted processing permission.
The hub has seven unique existing destinations, and all measured text/control
contrast and overflow checks passed. Planning fake-TTS regression is 2/2;
existing locale/Studio/composer source contracts are 26/26.

The mobile screenshot exposed installation/assistant buttons over the speed
selector. On Voice task screens only, retain installation on Account and move
the compact assistant control into the header's reserved area. Validate the
header and actual field hit targets again at 360/375/390 before accepting this
overlay correction. Voice Studio/composer full locale/density and quote/result
states remain open; no Voice family completion is claimed.

## Inventory checkpoint — current source

- [x] Keep the default marker and the server's status in vertical saved-voice
  cards. Use localized status text instead of the shared badge, which hides
  `read_only`/`ready`/`guarded`; do not change the shared badge.
- [x] Localize saved-voice option labels without changing the required field,
  IDs or the existing `profile && profile.id && profile.tts_ready` filter.
- [x] Real-render inventory check with populated UI-only fixtures: 24/24,
  VI/EN/ZH × light/dark × 1440/375; keyboard expand/collapse, ready-only
  selection, no horizontal overflow, no audio/player/download fabrication.
- [x] Final empty-state render recheck on the same source: 24/24. The final
  populated/empty matrices total 48 cases; UI-source hashes match between both.
- [x] Direct production-renderer Node regressions: 14 passed, 0 failed.
  Initial inventory RED was 8 failed/1 passed. The real-badge regression then
  exposed three blank statuses that a test double had hidden; corrected before
  acceptance and verified by browser-rendered localized status text.
- [x] Targeted Python locale/Studio/composer/delivery-safety: 27 passed in 2.12s.
  Expanded safety run: 102 passed/2 failed in 3.89s. Both failing test IDs also
  fail against immutable baseline `8a040d0`; no new failing ID remains.
  They are `test_video_music_and_dubbing_forms_forward_the_bot_planning_controls`
  and `test_guarded_feature_execution_keeps_web_authoring_primary_and_bot_companion_optional`.
  Keep these visible; do not claim the full safety module is green or restore
  outdated engine fields from this presentation task.
- [x] Migrate the preview-safety assertion from an obsolete literal to the
  localized authorized-preview copy and explicit no-player/link/action guard.
- [ ] Voice Studio/composer and their detail/version/cue-sheet states.
- [ ] Real quote/confirmation/progress/result/error presentation acceptance.
- [ ] Final shared motion gate; setup still logs the existing ViewTransition
  InvalidStateError. Do not report whole-app runtime as clean.
- [ ] Shared shell locale: the English desktop capture still shows Vietnamese
  navigation (`SÁNG TẠO`, `Tạo Ảnh AI`, `Tạo Giọng AI`, `Xuất bản & Lịch đăng`).
  These are observed remaining errors in Shared/Admin, not accepted English
  copy. The Voice inventory's locale pass does not cover the shared sidebar.

Evidence is under `qa/20261007-video-uiux/voice-inventory-populated-final` and
`voice-inventory-empty-final` outside the source repo. Fixtures alter only QA
browser presentation, not voice ownership, capabilities, Bot/engine or DB.
These Voice edits remain uncommitted/unpushed; production is still Video PR #616.

## Voice Studio list/new checkpoint

Scope: `/voice-studio` and `/voice-studio/new`; private profile authoring and
fixed presentation only. No detail/script/cue-sheet/composer completion follows
from these route checks.

- [x] RED: real renderer exposed mixed language in form/filter/default/event/
  pagination, plus optional-filter disclosure and current-nav label defects.
- [x] Natural VI/EN/ZH copy for forms, profile types, rights attestation,
  default marker, read states, filters, paging, event labels and policy.
  User profile names/content and language value `vi` remain unchanged.
- [x] List-first page; search field immediately visible; tag/state filters and
  create form are native keyboard-operable disclosures. `/new` opens creation
  first. All input names, maximum lengths, option values, required flags,
  capability checks and private action IDs remain unchanged.
- [x] Remove repeated technical intro/KPIs; keep actual profile list and
  history. Vertical fields/cards, no forced blank card heights; blue/teal
  theme unchanged. Mobile floating install control hidden with Account path
  retained; assistant moved to reserved header space on these routes.
- [x] Populated UI-only fixture matrix: 24/24 complete, VI/EN/ZH × two themes ×
  desktop/mobile; disclosure keyboard loop, consent/filter selectors, vertical
  fields and mobile hit targets pass. Text minimum 4.515:1, control-border
  minimum 3.399:1, zero page overflow and route runtime errors.
- [x] Final real-empty matrix: 24/24, same UI-source hashes as populated.
  Final list/new total: 48/48, no overflow, vertical create fields and working
  filter/consent selectors; text/border minimum 4.515:1 / 3.399:1.
- [x] Fresh Node aggregate: 38 passed/0 failed. Python navigation/locale/
  Studio/composer/delivery-safety: 42 passed in 3.54s. JS syntax, compile and
  whitespace checks pass; API/DB/engine/integration/motion/CI protected paths
  remain byte-identical to HEAD.
- [x] Extended navigation/locale/Studio/composer/safety run: 117 passed,
  the same two baseline test IDs failed in 4.65s. No full-suite PASS claimed.
- [ ] Known QA-only background GETs remain pending for core/status/auth/me/
  auth/providers/telegram connection. The earlier networkidle run terminated
  after 8/24 cases and is INCOMPLETE, never accepted as a full matrix. Runner
  now records expectedCases/completed and uses actual page plus signed Studio
  hydration readiness; pending requests remain explicitly visible, not hidden.
- [ ] Existing ViewTransition setup error; all-site/shared sidebar locale;
  Studio detail, script, versions, cue-sheet, composer and real flow states.

Final populated evidence: `qa/20261007-video-uiux/voice-studio-compact-populated-final`.
Final empty evidence: `qa/20261007-video-uiux/voice-studio-compact-empty-final`.
Both are QA artifacts outside the repo; no account or business record was created.

Next single slice: `VOICE-STUDIO-DETAIL-LOCALE-DENSITY` — inspect current
`renderVoiceStudioDetail`, `renderVoiceScriptCard`, `renderVoiceCueSheet` and
`voiceStudioScriptFields`; localize fixed detail/actions/confirmation/version
copy and fold long edit forms while retaining script text, metrics, IDs,
revision attributes, rights-revoked guards and all existing private controls.
Verify active/archived/revoked/missing/failed states, matching versus mismatched
cue-sheet receipts, VI/EN/ZH and mobile keyboard/hit targets. Do not execute
production mutations or create audio. Direction composer follows this slice.

## Voice Studio detail checkpoint

- [x] Localize detail hero/section, profile state, rights-revoked notice, editor,
  composer, script editor/actions, version history, activity and safety boundary.
  Source/content names remain user data; IDs, revisions, capability checks,
  consent-revoked lock and action attributes remain unchanged.
- [x] Localize script kinds, source labels, cue-sheet metrics and action labels;
  remove raw technical English from VI/ZH detail output. English uses the same
  catalogue keys, not mixed fallback copy.
- [x] Active detail UI-only fixture: 12/12 complete; one real script, one
  matching local cue-sheet, two profile versions, no audio/table, no overflow;
  VI/EN/ZH × light/dark × 1440/375. Min text/border 4.515/3.399.
- [x] Revoked-consent detail fixture: 12/12 complete; localized revoked-rights
  notice, no provider/player/table, no overflow; min text/border 4.515/3.399.
- [x] Fixed detail surface uses blue/teal semantic tokens; quiet buttons and
  dark labels meet the same contrast comparator. Known setup ViewTransition
  warning is isolated in `setupRuntime`, not route runtime.
- [x] Detail Node locale contract: 3/3. Aggregate current Voice Node tests:
  41 passed/0 failed. Python focused current run: 117 passed plus the same two
  baseline failures; no new failure ID.
- [x] Missing/loading/failed/guarded/wrong-record and mismatched cue receipts
  verified by direct production-renderer behavioral tests in the 2026-10-08
  re-audit below; not inferred from active/revoked screenshots.
- [x] Direction Composer progressed to actual-receipt re-audit below.

Detail evidence: `qa/20261007-video-uiux/voice-studio-detail-populated-final7`
and `voice-studio-detail-revoked-final4`. These are isolated QA fixtures only.

## Direction Composer checkpoint

- [x] Composer form, empty result, result metadata, three-option comparison,
  warnings/review list, scope guard and fixed buttons use catalogue keys in
  VI/EN/ZH. Raw user direction text remains untouched.
- [x] No raw technical mixed labels remain in the Composer result source:
  `Use case`, `Style prompt`, `Delivery notes`, provider/job/payment guard
  labels and execution-boundary labels now render via localized copy.
- [x] Browser matrix: 12/12 complete, VI/EN/ZH × light/dark × 1440/375;
  no overflow/runtime errors. Text minimum 5.944:1, control-border minimum
  3.399:1. No provider, audio, wallet or persistence action was submitted.
- [x] Aggregate current Node Voice tests: 44 passed/0 failed. Python focused
  current run: 117 passed plus the same two baseline failures; no new failure ID.
- [x] Actual server-composer receipts and negative receipt clearing verified
  in the 2026-10-08 re-audit below. Provider/audio/DB I/O blocked in generator.
- [ ] Shared shell locale, known setup ViewTransition warning, quote/progress/
  result UI for TTS and final all-site motion gate remain open.

Composer evidence: `qa/20261007-video-uiux/voice-direction-composer-final3`.

## Voice bridge-backed state readback

- [x] Fresh read-only matrix for `/voice/tts`, `/voice/saved`, `/voice/clone`,
  `/voice/preview`, `/voice/outputs`: 60/60 complete, VI/EN/ZH × light/dark ×
  1440/375; no overflow/runtime errors, text minimum 4.515:1 and border
  minimum 3.399:1. This proves presentation/readiness surfaces only.
- [x] TTS quote/confirmation/progress/result/error presentation verified with
  UI-only fixtures on `/voice/tts`: 72 primary cases + 36 boundary cases,
  VI/EN/ZH × light/dark × 1440/375; dark/light text contrast 4.515:1 / 5.473:1,
  zero overflow and route runtime errors. The 60 read-only cases remain the
  separate evidence for `/voice/preview` and `/voice/outputs`; they do not
  prove quote-state behavior on saved voice or clone.
- [x] Saved-voice and clone quote/progress/result states have separate
  route-specific evidence: 144/144 cases on `/voice/saved` and `/voice/clone`
  across VI/EN/ZH × light/dark × 1440/375. A corrected interaction matrix
  verified flow-before-form for all six states, keyboard disclosures, the
  collapsed prior form, quote gating, no cost leak, zero overflow and zero
  route runtime errors (48/48 interactions).

## TTS flow-state checkpoint — 2026-10-08

- [x] Direct renderer tests: 45/45 passed; six-file Voice UI aggregate:
  110/110 passed. `node --check` passed for `portal.js` and `portal-i18n.js`;
  `git diff --check` passed.
- [x] Localized the disabled Voice form tooltip for VI/EN/ZH. Dark-mode Voice
  flow text now uses the readable semantic foreground rather than the muted
  shared page color that measured 3.51:1 before this fix.
- [x] Existing submit/confirm gates, action IDs, feature aliases, receipts,
  tracking match rules and form fields remain covered by direct behavior tests.
- [x] QA artifacts: `voice-tts-flow-final-20261008/browser-review.json` and
  `voice-tts-boundary-final-20261008/browser-review.json` under
  `qa/20261007-video-uiux/`. Both are isolated presentation fixtures; no
  business POST or paid action was made. Four background auth GETs remained
  pending, and the setup `ViewTransition` warning remains an open motion item.
- [ ] Voice release/CI, shared English-shell copy, remaining route-state
  evidence and whole-site motion/performance checks remain open.

Saved-voice and clone evidence: `../../../../../qa/20261007-video-uiux/voice-saved-clone-flow-20261008/`
and `../../../../../qa/20261007-video-uiux/voice-saved-clone-interaction-20261008/`.

## Receipt/locale re-audit — 2026-10-08

The prior Composer 12-case pass covered the empty/form screen, not a valid
result. The old QA runner mounted two fixtures; the second overwrote the full
receipt with `{composer: ...}`. Removing that QA duplication and using receipts
from the unchanged server composer exposed real presentation defects; this
checkpoint supersedes broad earlier Composer-copy claims.

- [x] Server-generated core/extended receipts retained in
  `tests/fixtures/voice-direction-composer-receipts.json`. Generator calls only
  the deterministic server functions with network/SQLite disabled; no account,
  persistence, provider, job, wallet or engine API action.
- [x] Replace source-grep locale tests with direct execution of the production
  normalizer, form and result renderer. Initial RED: 9 failed/3 passed. Form
  options/help mixed languages; result exposed internal option IDs and four
  note keys. Field names/values/limits and strict receipt validation unchanged.
- [x] Translate five fields/options, page/document/current-nav titles and
  four note labels; hide internal IDs, translate `off`; display exact canned
  guidance through UI catalogue without changing user text, unknown text or
  the source receipt. Invalid/provider-called/mismatched receipts stay empty.
- [x] Remove repeated intro/count panels; form first, vertical fields/options,
  scope disclosure keyboard-operable. Mobile first textarea is now visible
  around y=364–388 instead of y≈1,100. Blue/navy palette unchanged.
- [x] Fix the empty assistant button: hide its label only, retain the chat SVG.
  Mobile icon visible in header; installation remains available on Account.
- [x] Core receipt matrix: 12/12. Extended receipt + valid→invalid clearing:
  12/12. Both VI/EN/ZH × light/dark × 1440/375, three choices, preserved custom
  input, no fake audio/table, no overflow/runtime, keyboard scope/selection.
  Invalid state clears the prior sample instead of displaying stale output.
- [x] Final combined core+detail matrix `voice-receipt-detail-settled-20261008`
  is 24/24, source-stable, zero overflow/route runtime, text min 4.515:1 and
  control border min 3.399:1. Known setup ViewTransition warning retained.
- [x] Independent settled mobile visual: both themes, computed opacity 1 for
  all checked text/ancestors, no finite animation running. This is screenshot
  readiness only; not the final motion smoothness/performance gate.
- [x] Detail behavioral renderer tests now cover missing/loading/failed/wrong
  record, revoked/archived capability locks and mismatched/provider/audio cue
  receipts. Also fix blank status label, missing version-restore label and
  mislabeling `local_deterministic_draft_only` as manual. Source/IDs unchanged.
- [x] Node aggregate 65 passed/0 failed; Python contracts 41 passed; extended
  safety run 117 passed/2 matching baseline failures. API/DB/engine/integration/
  motion/CI protected paths byte-identical to Video merge base `8a040d0`.
- [x] TTS quote/confirmation/progress/result/error presentation is completed
  in the 2026-10-08 checkpoint below.
- [ ] Whole-site shared locale and motion gates remain open. No Voice release
  or live-production outcome is inferred from these isolated QA results.

Current evidence: `qa/20261007-video-uiux/voice-receipt-detail-settled-20261008`,
`voice-direction-extended-invalid-final`, `voice-composer-settled-visual`.
Earlier failed/incomplete fixture attempts are retained and are NOT PASS.

Code checkpoint: `2983174f33cde489a182b2523b328f8ce0b01c4d`, local only.
TTS flow-state presentation is complete in the checkpoint above. The ordered
Music UI slice is now separately verified locally; SubDub is next. Voice and
Music are not yet committed, pushed, merged or deployed; remaining Video and
the site-wide motion gate stay in the Owner's queue.
