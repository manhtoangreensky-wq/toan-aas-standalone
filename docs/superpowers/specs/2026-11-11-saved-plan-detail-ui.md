# Saved-plan detail UI — focused contract and audit

BATCH=VIDEO-SAVED-DETAIL-UI; BASE_SHA=652af67d8ba4706718f458ee1b26ad62bcc0b8ef.
Branch=codex/video-saved-detail-ui-20261111; product=standalone WebApp;
tracker=Issue689. PR716 already merged/deployed/verified; do not redo its flows.

## Bounded design / evidence

Use existing brand/theme tokens, forms, controls and navigation. No redesign,
new dependency or shared interface. Owner authorizes routine UI choices within
the active goal without further approval prompts. Three independent output-only
Antigravity3.8FlashHigh packets; coordinator applies accepted fragments serially.

| Defect | Principle / consequence | Measured evidence | Severity / confidence | Fix |
|---|---|---|---|---|
| Insufficient supporting-text contrast | WCAG AA / labels hard to read |84light samples below4.5, min1.3183666806932544:36form-note+48small |3/high |Scoped existing --portal-muted, no global color changes |
| Redundant explanation and vanity metrics | Nielsen8 / editor pushed below repetition |List intro, repeated boundary cards, internal boilerplate in5renderer functions |2/high |Remove exact noninteractive markup; keep forms/controls/history |
| System-centric decoration | Nielsen2/8 / English/internal IDs dominate actual plan |VIDEO PRODUCTION STUDIO eyebrow; known generated-tag chips |2/high |Hide only feature eyebrow; filter exact finite system tags from decorative chips, preserve custom/unknown tags and every stored/form value |
| Excessive summary card density | Hierarchy/proximity /3facts consume mobile space |Three stacked status/revision/scene summary boxes |2/high |Compact wrapped inline dl, keep all3facts |

Brand, real plan headings, customer text, safety checks and6actual saved plans are
working and protected. No new palette/typeface. Reuse --portal-ink/--portal-muted;
4/8spacing,12pxcaption/14pxvalue,1.5line-height. Inputs keep mobile16px.
PWA offline-mid-write, update receipt on physical devices, standalone/back/Safari
remain whole-goal gates, NOT_TESTED in this audit. Do not infer failure from a
screenshot or change service worker/auth/session here. Motion remains last.

## Ordered queue / application allowlist

| Order | Spec | Result / dependency | Status |
|---|---|---|---|
|1|VDUI-CSS|Contrast, hidden redundant eyebrow, single-column create layout, compact3factsummary; independent|LOCAL_GATE_PASS_R2|
|1|VDUI-LIST|Exact list intro/boundary/internal paragraphs removed; forms/actions preserved|LOCAL_GATE_PASS_R1|
|1|VDUI-DETAIL|Exact detail/runtime/scene boilerplate removed; finite machine-tag chip projection only|LOCAL_GATE_PASS_R2|
|1|VDUI-READABILITY|Measured extra light labels/surface/mobile font prerequisite|LOCAL_GATE_PASS_R1|
|1|VDUI-SECTION-LOCALE|One resolved display-data section leaf localized|LOCAL_GATE_PASS_R1|
|2|VDUI-ACCEPTANCE|Combined diff review, renderer/control parity and native light/dark/read-only flows|LOCAL_GATE_PASS|
|3|VDUI-SHIP|Docs/tester/metadata/provenance -> exactHEADCI/merge/deploy/runtime/assets|WAITING|

Application edits ONLY static/portal/portal.js exact agreed function fragments
and append-only scoped static/portal/portal-theme.css. No other app file/import/
signature/global constants/helper/renderHero/normalizer/integration/i18n/backend/
auth/CSRF/session/rights/provider/engine/wallet/PayOS/Bot/route-engine/ENV/schema/
motion/service-worker/deploy-workflow changes. No production data mutations.
Keep178VideoStudio catalogue keys and allVI/EN/ZH values unchanged. Keep raw
tags/customer data and editable field values; chip projection is not data rewrite.
Unknown tags, ordinary custom tags, and ambiguous two-origin records stay visible.
Raw internal-tag text editing semantics remain a separate later goal item; do not
pretend hiding decoration translates or migrates those values.

Exact JS functions allowed: renderVideoStudio (list); renderVideoStudioDetail,
videoRuntimeEstimateMarkup, renderVideoSceneCard (paragraphs only),
renderVideoStudioTags (same signature/return-type, finite chip filtering only).
Keep now-unused renderVideoStudioBoundary definition to avoid unrelated cleanup;
only its two display callsites removed. No symbol rename/interface expansion.

Impact scan: `git grep -l -F renderVideoStudioTags -- .` ->1file,
static/portal/portal.js. Source occurrence inventory: definition18671;
callers18749(plan card),18793(scene card),18830(detail summary). Four occurrences,
same closure/file; no export or cross-file consumer. Same-signature HTML-output
change protected by full renderer fixtures and interactive-attribute parity.

Test allowlist: new tests/saved-video-detail-ui.test.mjs,
tests/helpers/saved-video-detail-context.mjs; dependency-only fixture injection
in tests/video-uiux-locale-presentation.test.mjs for7existing option Sets read
from actual production declarations (no duplicate catalog/test redefinition).
One CI invocation permitted. Ops/original-feature/case/Tester/provenance and
generated Tester local-file metadata updated before push; no weakening tests.

## Checklist before and after build

- [x] RED real renderer: list/detail noninteractive clutter and machine chips.
- [x] Native BASE evidence:84supporting-text failures, real saved-field data,
  both themes observed; original6plan18scene database/evidence retained.
- [x]3independent output-only workers return exact records, no shared writes; bounded prerequisites retained.
- [x]Combined source review: every app byte outside agreed spans/CSS suffix/section leaf unchanged.
- [x]Renderer GREEN; custom/unknown/prototype/lookalike/ambiguous tags preserved, raw context intact.
- [x]BASE/candidate form/control attribute+label parity across VI/EN/ZH and states.
- [x]Native320/360/1440, light/dark: zero overflow, supporting text>=4.5,
  actual themeflags/palette; eyebrow/boundary/intro absent,3facts retained compactly.
- [x]Keyboard/focus/font>=16mobile, readonly/archived/empty/error/guarded semantics kept.
- [x]Owned copied DB actual GET/reopened fields unchanged;0compose/save/provider/
  wallet/production/.env/media accesses; source/evidence binding and Job->0.
- [ ]Ops/original-feature/Tester/canonicalcase+local-file-metadata/provenance ready.
- [ ]ExactHEADCI/merge/exactSHAdeploy/runtime/assets receipt on Issue689.

Commands: node --test tests/saved-video-detail-ui.test.mjs ->zero failures after
patches; node --test tests/video-studio-vi-locale.test.mjs
tests/video-uiux-locale-presentation.test.mjs ->regressions pass. Browser plugin
absent; use owned localhost Chrome/Playwright, never disabled production browser.
No full saved-copy persistence rerun; new unit uses existing-plan read-only QA.
Worker R1 then same-spec R2 only for a real mismatch; two genuine failures before
direct application repair. Spec/test/harness omissions are coordinator errors.

Test-maintenance amendment after exact group application:36newtests passed and
48view/1392interactive-attribute parity passed. Existing9assertions still require
the deliberately removed intro/boundary copy (7VI literalvisibility,2EN/ZH intro
kickers). Allow tests/video-studio-vi-locale.test.mjs to retain exact catalogue
values but assert7removed literals absent; preserve4meaningful visible literals.
In the isolated UI test replace only2removedintro labels with literal existing
create-form titles. No key/hash/action/field/readonly/history assertion removed.
Add3ambiguous-origin tag preservation cases. Rerun only affected9+new3tests,
retain61passes; finalCI runs full73. Native observes stable finite animations
before sampling colors/layout, without changing application motion or CSS.

## Native prerequisite VDUI-READABILITY — new baseline findings

First native54views finished:15passed/39failed,1332storedfieldmatches exact,
6plan18scene/hash/originalevidence unchanged,72ownedJobprocesses->0.24mobile
detail views fail actual15px inputs;15light views stop on a palette-harness
assumption about decorative body gradients, and their captured text measurements
also reveal genuine label/helper failures:14samples/list and50/detail at1440,
minimum1.2653297845023375. Field labels still use legacy light text on white;
runtime metric cells retain dark translucent backgrounds. These are additional
baseline font/theme-role gaps, not an incorrect implementation of exact prior
CSS targets. Keep VDUI-CSSR1/R2 and DETAILfailure history unchanged; no reset.

Add prerequisite VDUI-READABILITY R1: only append semantic-token light label/
supporting-text/runtime-cell rules and scoped mobile16px controls to sameCSSfile.
No other app/interface/data/motion change. Preserve73Nodeaccepted cumulative and
48view/1392controlparity. Correct palette inspection: actual root/body theme flags,
colorScheme and solid editor surface prove theme; decorative body gradient base
colors remain recorded for visual review, not treated as text contrast. ALL
indeterminate or below4.5 text samples remain blocking; do not relax them.
Preserve initial native evidence and rerun only39failed views after the added
prerequisite;15unaffected dark cases retained with source/computed-rule comparator.

VDUI-READABILITYR1 exact worker append accepted. Failed-only39views nowpassed,
15unaffected retained ->54aggregate;1332fieldmatches/6plan18scene unchanged.
2718recheckedtextsamples min5.331309340518602,0indeterminate;summary320max54px,
primarybuttonmin44px,57ownedJobprocesses->0. Bodygradients visually reviewed in
VI320light/dark andZH1440light; no numeric body-pixel-contrast claim.

Visual review additionally found the desktop breadcrumb still displays raw
Video Production Studio inZH. Add VDUI-SECTION-LOCALE R1 as a distinct locale
prerequisite: only the section data leaf in resolvePage's exactUUIDvideo detail
branch may change to videoStudioText('page.title',existingVIfallback). No shared
helper/signature/i18n value change. Render resolves the page anew at42445; section
is display metadata. Keep all previous code, palette/data/control proofs. Three
new real-renderer cases must RED thenGREEN; a scoped header-only native supplement
checks3locales at320/1440 rather than repeating54layout/readback cases. Full UI
unit76tests after these3checks; all earlier73accepted evidence retained.

Reusable local evidence:11/11 PR716 failed firstCI only because canonical case
source statistics were not refreshed; update reports/migration/p0-05d-tester-
workspace.json metadata from normalizedLF bytes whenever case source changes.
All historical remote/P0/48case fields stay unchanged. No global lesson promotion.

## Same-spec R2 gate before application

R1CSS/LISTpayloads match exact contract. DETAIL has exactly one wrong OLDanchor:
activity.description paragraph ends `</span>` instead of actual/spec `</p>`.
Seven other records and NEWhelper body match; count one genuine DETAILhandoff
failure, no source applied. R2 corrects that OLDdescriptor only, not NEWcode.

Preflight also read legacy portal.css:1921: summary fact divs have min-height106px.
The coordinator's compact CSS target omitted resetting it. CSSR2 adds ONLY
min-height:0 inside the prescribed scoped summary-child rule. This is a missing
coordinator criterion, NOT a CSSworker failure. Keep all other CSSbytes and both
other worker results. Native<=72px summary height remains required; do not relax
the test. Two independent output-only R2 corrections, sameSPECIDs/history.
Full goal/old-record/title/stale/retry/auth/device/signedLIVE/motion remain open.
