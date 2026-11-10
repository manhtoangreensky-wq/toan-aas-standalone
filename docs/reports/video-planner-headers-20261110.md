# Eight video-planner headers — combined acceptance, 10/11/2026

TASK=VIDEO-PLANNER-HEADERS-ABC; LOCAL_ACCEPTED; delivery gates remain separate.
BASE_SHA=564467fbc04cf7445e09bb9d74ed1ea10de0487f.
Branch: `codex/video-planner-header-locale-20261110`. Tracker: Issue #689.
HEAD_SHA=the source commit containing this report; final provenance/CI receipt
records immutable delivery revisions without a self-referencing commit hash.

## Scope and current behavior

Only dynamic H1, document title and description for these exact routes changed:

- `/video-studio/prompt-planner`
- `/video-studio/idea-planner`
- `/video-studio/self-shot-planner`
- `/video-studio/script-to-screen-planner`
- `/video-studio/cinematic-concept`
- `/video-studio/image-motion-planner`
- `/video-studio/reference-format-planner`
- `/video-studio/storyboard-composer`

Three output-only Antigravity tasks supplied16new keys per locale through three
separate namespaces. Patches were applied sequentially. All9493prior entries
per locale remain unchanged. Routes, helper signatures/fallbacks, controls,
form/result contents, customer/server text, private guards and actions are not
changed. The descriptions describe planning, not generated media or delivery.

## Single acceptance ledger

| Gate | Actual result | Reuse / limitation |
|---|---|---|
| Real renderer inventory |24renders;8English descriptions were Vietnamese,3VI titles English,1VI title used generic prompt |Baseline48checks:24protected pass/24locale RED |
| Combined worker candidate |47/48; one Chinese self-shot sentence contained Vietnamese |Only that sentence returned to worker R2 |
| Correction |1/1affected check, exit0 |47retained+1corrected=48; no blanket rerun |
| Focused regression |139/139, fail0, exit0 |63new-header+24outer+45result+7media-purity |
| Native acceptance |48/48, fail0 |8routes x3locales x320dark/1440light; not crossed themes |
| Native observations |0pageerrors,0external requests,0product writes after setup |Console events were not collected; no console-zero claim |
| Source/protected review |Exact combined worker source;9protected files unchanged |Integration/CSS/auth/motion/app/pages/video backend/deploy workflow |
| Resume binding |Current3JS files match native before/after hashes |Evidence reused; no rerun of accepted native or Node tests |

Focused command already completed:
`node --test tests/video-planner-header-locale.test.mjs tests/video-planning-outer-locale.test.mjs tests/video-planning-result-locale.test.mjs tests/media-studio-vietnamese-purity.test.mjs`.
The recorded TAP ends with tests139/pass139/fail0. CI is a separate environment
gate, not a repeated local acceptance run.

Canonical LF SHA256 of accepted application source:

- portal.js: `d260d8b911ae18464f7d6592b0cb633562696ffa083fde644f9ad93fa9cf3569`
- portal-i18n.js: `0864ecc5b0398999a6e58503e14bebaa1f3983266fa4cd83b52ba0bedebea754`

Evidence files in the existing local artifact store:
`video-planner-header-focused-nov10.tap`,
`video-planner-headers-candidate-nov10/accepted-summary.json`,
`video-planner-headers-source-review-nov10.json`, and
`video-planner-headers-native-nov10-combined-accepted/summary.json` with screenshots.
Native runner uses temporary signed QA accounts/SQLite/assets, one session per
locale in RAM, GET/HEAD only after setup and cleanup in finally. A read-only
hydration Promise observer does not change committed app code or force visibility.

## Pre-push / tester / remaining requirements

Operations and original-function comparison are updated in `TAI-LIEU/01` and
`TAI-LIEU/02`; tester session `VIDEO-HEADERS-20261110` is READY with completed local
evidence. Existing issue templates, measured workflow labels and historic cases
are reused, not recreated. GitHub Projects cannot be re-read with the current
token (missing read:project); no login or scope change is made. The independent
local tester session and single tracker Issue #689 remain usable.

Inner content still mixes languages: the script-to-screen mobile screenshot
contains the existing English planning-layer badge and mixed brief/storyboard
copy below the corrected header. **Whole-page locale is not accepted.** These
inner forms/results are next in the ordered ledger. Signed production output,
server first paint, device/Safari, keyboard/recovery, auth lifecycle and final
motion/performance remain open. No full local Node/Python matrix rerun is claimed.

FILES_CHANGED=2appJS,1newheaderTest,1boundedcatalogSnapshotAmendment,1CIstep,
scopedoperations/tester/spec/ledgerdocuments; provenance follows source commit.
BASELINE_FAILURES=24localechecks; BRANCH_FAILURES=0in declared gates;
NEW_FAILURES=0in comparable header/protection checks.
PROTECTED_COMPARATORS=existingcatalog/routes/controls and9protectedfiles unchanged.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
DEPLOY=NOT_YET; LIVE_PASS=NOT_TESTED; BLOCKERS=NONE for this delivery unit.
LESSON_CANDIDATE=NONE. Whole goal remains active.
