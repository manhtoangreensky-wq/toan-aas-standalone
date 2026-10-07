# Voice UI closeout — 2026-10-07

Owner order: Voice → Music → SubDub → other features → unfinished Video.
Base main: `8a040d0c2af0cdcb2ebd89a27f5f2caa9beff952` after Video PR #616.

## Contract

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
- [ ] TTS and saved voice: content → voice → speed → volume, vertical inputs,
  visible primary action, truthful readiness and quote/confirmation states.
- [ ] Clone: supported consent/sample/name sequence and clear availability.
- [ ] Preview/output: genuine result/delivery state without fabricated audio.
- [ ] Voice Studio/composer: separate metadata/text planning from speech creation;
  layout and fixed copy natural and localized, preserve actual private controls.
- [ ] Per-route VI/EN/ZH × light/dark × desktop/mobile browser checks, keyboard,
  text/control contrast, overflow and visual screenshot review.
- [ ] Source contract/syntax checks, updated checklist/evidence then review.

Scope: Voice presentation and fixed feedback text only. Paid provider calls,
production business actions, API/engine/wallet/ENV changes remain zero.
Do not reuse the older dirty UI worktree as the engine/runtime authority.

Status: `CORE_AND_INVENTORY_CHECKPOINT / STUDIO_LIST_NEW_LOCAL_VERIFIED / DETAIL_COMPOSER_NEXT`.

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
- [ ] Missing/failed/no-detail server states and mismatched cue receipt need a
  direct UI-only fixture check; do not infer them from active/revoked evidence.
- [ ] Direction composer is the next single Voice slice.

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
- [ ] Composer result fixture with a real deterministic server receipt, and
  final missing/failed/mismatched cue receipts. These require safe QA fixtures,
  not production/provider calls.
- [ ] Shared shell locale, known setup ViewTransition warning, quote/progress/
  result UI for TTS and final all-site motion gate remain open.
