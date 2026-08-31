# MOTION-WEBAPP-SURFACES-001 — live-reopen v2 evidence

## Outcome

Customer Web motion is observable on the real Portal routes without changing Admin/Auth/Landing timing, without replaying a route entrance during same-route hydration and without making semantic content depend on JavaScript motion. This report proves the local candidate only; it does not claim push, merge, deploy or production LIVE behavior.

## Source identity and integrity

- Repository: `manhtoangreensky-wq/toan-aas-standalone`.
- Current rebased base: `0dd8ffa3503436cb7431a98a882ff99cc25588d8`.
- Original stacked base before PR #417/#419 merged: `eeb85107dd9ebf391db5a155243da8f45d8600cd`.
- Accepted candidate worktree: `manager/motion-webapp-surfaces-live-reopen-v2-20260830`.
- Exact runtime paths: `static/portal/portal-features.js`, `portal-motion.js`, `portal-theme.css`, exact `mountWorkspaceMotion()` hunk in `portal.js`; one new test file.
- Runtime numstat: feature entry `+71/-0`, motion helper `+80/-13`, theme `+111/-0`, Portal monolith `+10/-0`; final contract test asserts the exact 16-path committed stacked-PR diff and dedicated PR-workflow coverage.
- A previous Primary worktree was rejected before commit because a Windows patch operation truncated `portal.js`; none of its code or test claims were used for acceptance. v2 was rebuilt from the exact base, and the final patch applied on Linux with `portal.js +10/-0`.

## Root causes proven

1. Customer motion inherited shared `140/220/420ms`, `10px`, `.96→1` and `34ms` stagger, making it nearly invisible.
2. Same-route hydration unmounted workspace presentation, replaced child DOM and skipped remount; active motion could be canceled and final DOM lost scroll observers.
3. Child `animationend` events could bubble to the stable main and clear its route marker early.
4. `/features` intentionally loads only `portal-features.js`, so shared Portal motion could not affect it.
5. Animating/layouting all 135 feature cards produced a long animation frame. Hero-scoped entrance plus `content-visibility:auto`/intrinsic size retained DOM/search and removed feature-route long tasks over 200ms.

## Implemented bounded behavior

- Customer-only tokens: control `180ms`, state/navigation `360ms`, entrance `680ms`, stagger `80ms × max 6`, distance `20px`, opacity `.12→1`, optional `.985→1`.
- Shared `:root` tokens remain `140/220/420ms` and `10px`; Admin/Auth/Landing do not inherit the longer customer entrance.
- A stable main route marker survives same-route hydration until its own `animationend`; bubbled child events are ignored.
- Hydration settles in-viewport replacement targets and re-arms only offscreen targets. Observer, fallback scroll/resize listener, RAF, timers, focus and reduced-motion listener have cleanup.
- `/features` retains its split bundle and adds only presentation lifecycle inside `portal-features.js`; existing API reads are unchanged and no full Portal asset is loaded.
- Reduced-motion keeps content at opacity `1` with presentation animation/transition/transform disabled.

## Verification

### Independent Tester

- `VERDICT=PASS`, findings `P0:0/P1:0/P2:0/P3:0`, `FILES_CHANGED_BY_TESTER=0`.
- Focused six-suite gate: `51 passed in 3.01s`.
- Candidate comparator: `4 failed, 29 passed`; clean base comparator: `4 failed, 29 passed`; exact four failure IDs match, `NEW_FAILURES=0`.
- Node syntax: feature entry/motion/Portal `0/0/0`; `git diff --check=0`.

### Linux VPS isolated worktree

- Worktree v3 from exact base, patch SHA-256 `fb9e80ba8f919f8cd0b789af8ad7f0b175b3f88be29a88433166555efb33a854`.
- `git apply --check --whitespace=error-all`: PASS; final `portal.js +10/-0` on Linux.
- Focused six-suite gate: `51 passed in 6.61s`.
- Comparator: candidate `29P/4F`, same exact four IDs as base; `NEW_FAILURES=0`.

### Rendered signed local matrix

- Four real routes × desktop/mobile × normal/reduced = `16` cases using an isolated SQLite database and local signed test account.
- Repository matrix candidate: `95` lines / `6115` bytes / SHA-256 `0f21fc6a2bcced8b6f7cb507a1b6d0629d9a44acd9f72bbf4625abeb68d14bdc`.
- Normal routes have `portal-customer-observable-enter` at `0.68s`; routes with offscreen groups have scroll reveal at `0.68s`.
- Reduced routes show animation `none`, opacity `1`, transform `none` and full content.
- `16/16` content visible; overflow X `0`; CLS `0`; page errors `0`; request failures `0`; recorded HTTP errors `0`; foreign requests `0`.
- `/features` desktop/mobile after containment: long tasks >200ms `0`.
- Dashboard has one long task in both normal and reduced runs; Long Animation Frame attributes it to pre-existing Portal/integration render/layout. It is not a motion regression and remains a Customer Final performance debt.
- Desktop console reports only the local fixture `/favicon.ico` 404; the same baseline run has it, and `requestfailed/httpErrors` tracked by the runner remain `0`.

### Fresh post-rebase rendered closeout

- Runtime source `f8caa78a6d48f7cfa58573ec64eaf74df322bb1e` was rendered from the clean rebased worktree at evidence parent `7151fb09969fba5ab73876805685da5a3c4b9775`; the test server used isolated `app.db`/`sessions.db` files under the workspace.
- The Codex in-app Browser was the primary interactive surface. Signed navigation reached `/dashboard`, `/features`, `/studio` and `/wallet/topup`; page title/DOM were non-blank, framework overlay count was `0`, console error/warning count was `0`, and horizontal overflow was `0` at `1440x900` and `390x667`.
- A real `/features` scroll changed pending targets `11→10` and visible targets `0→1`; the revealed target computed `portal-customer-observable-enter` at `0.68s`. This is the interaction proof, not a source-only assertion.
- The in-app Browser does not expose reduced-motion emulation, so the existing bounded Chrome-headless runner was used only for the responsive/reduced-motion matrix. The fresh run retained `16/16` visible routes, `8/8` reduced-motion static routes, overflow `0`, page errors `0`, failed requests `0`, recorded HTTP errors `0` and foreign requests `0`.
- A full-run `t80` sample can arrive after an entrance when screenshot capture or a busy main thread delays observation. The screencast frames still record the customer main moving from the `.12` entrance frame to opacity `1`; a quiet focused `/features` rerun then recorded desktop/mobile entrance or hydration markers, both scroll reveals at `0.68s`, CLS `0`, and long tasks over `200ms` equal to `0`. The focused result is used instead of treating that sampling delay as a product failure.
- The fake local account intentionally had no canonical link and the fixture intentionally had no Bot bridge, so the manual-topup pane remained guarded. No form was submitted. This is not a motion regression; the protected manual-topup source remained unchanged and the unlinked-account/customer-native requirement is carried to Customer Final rather than mixed into this motion branch.
- Fresh focused contracts after the evidence refresh: `56 passed, 1 deselected`. The three-file stale-contract comparator was executed on both exact `origin/main` (`0dd8ffa`) and the candidate: both returned `22 passed, 5 failed` with the same five test IDs, including the old Landing `portalMotionSkipEnter` string assertion; therefore `NEW_FAILURES=0`. The earlier four-failure comparator remains accurate for its original two-file scope.
- Independent review then found two lifecycle boundary defects before push. TDD reproduced both: Customer motion selectors were keyed by non-Admin `app-kind` and could reach Landing/Auth, while a child `animationend` or stale timeout could consume/cut a newer entry. The final source keys the live-reopen block by exact `data-portal-surface="customer"` and keeps one generation-scoped listener/timer per element; a new native-`once` harness proves child and stale callbacks cannot clear the active marker.
- Post-fix computed styles: signed Customer reports `surface=customer`, fast `180ms`, entrance `680ms`; public Landing reports `surface=landing`, fast `140ms`, no Customer entrance token; guest Auth reports fast `140ms`, no Customer entrance token, content visible, overflow `0`, console errors `0`.
- Post-fix focused contracts: `57 passed, 1 Windows-only deselected`. The protected Auth/Landing suite remains `30 passed` plus the same one stale Landing string assertion already proven on exact main; `NEW_FAILURES=0`.
- Final post-review render still has `16/16` visible, `8/8` reduced static, overflow/page/request/HTTP/foreign-request failures `0`; `/features` full-run sampling is covered by the already-hashed focused desktop/mobile evidence and the in-app Browser scroll proof.

Large artifacts are outside Git. Final post-review full matrix summary SHA-256: `ea40a657afa23103cfc9b77be8056eaede2b694434ed4c19a46331a158da864a`; desktop MP4 `5da238ce48cc7def41f946dab87cdef6f314ca2000a7f563b5d0a61c48ceb18f`; mobile MP4 `76e19c90b696542010c5b780f7c8af69c96a2806e583fa7990fb8fafd70d62a3`; focused `/features` summary `102af64754d6871abf808d5bcb5069f6c731a7ab421efb177320eef7ac69ca74`.

### Final Tester workspace closeout

- Canonical source contains exactly `WA-01..WA-36`; P0 case count remains `18`; WA-35/36 are both `local-render` under `MOTION-WEBAPP-SURFACES-001`.
- Windows raw Tester suite: `28 passed / 1 failed`; the only failure is the unchanged POSIX `0600` mode assertion reporting `0o666` on Windows. The functional run with that exact platform-only assertion deselected is `28 passed / 1 deselected`.
- `tester_case_sync.py --bo=34 --so=2 --json` emitted exactly WA-35 and WA-36, both `dry_run=true`; GitHub mutation count `0`.

### PR quality gate coverage

- `.github/workflows/webapp-quality.yml` now syntax-checks both changed split/shared motion runtimes: `portal-features.js` and `portal-motion.js`.
- The bounded PR suite runs `test_motion_webapp_surfaces_live_reopen_contracts.py` and the complete `test_p0_05d_tester_workspace.py`; Linux CI is therefore the canonical `0600` permission gate.
- Final Manager focused gate after the CI artifact regression test contains `53` passing tests; the earlier Independent Tester receipt remains `51 passed` because it predates the workflow-coverage and artifact-isolation assertions.
- Initial PR #418 run `33331043771` reached `248 passed` before failing: earlier API tests created untracked `toandaas_system.db`, while the scope assertion incorrectly inspected runtime `git status`. Root-cause fix reads `git diff --name-only eeb8510...HEAD` instead, so generated runtime artifacts cannot masquerade as committed source scope.
- TDD receipt: the new artifact-isolation test first failed with `NameError: committed_paths_since_base is not defined`, then passed `2/2` after the minimal Git-history helper was added; the fixture removed its DB file.
- Second PR #418 run `33352316673` passed the artifact scope and reached `277 passed`, then exposed a separate portability defect: readiness stored raw Windows CRLF byte/hash (`3211`) while Linux LF checkout measured `3098`.
- Portable metadata TDD: LF/CRLF equivalence first failed with `NameError: portable_text_bytes is not defined`; after adding the minimal newline normalizer, the helper test passed and the old readiness data failed exactly `3211 != 3098`. Schema `p0-05d.v2` now declares `metadata_encoding=utf-8-lf-portable` and all six file records were remeasured.
- Exact 35-target bounded workflow after both fixes: `278 passed, 1 deselected, 1 warning` on Windows. Tester functional gate is `28 passed, 1 deselected`; the only deselection is the already documented POSIX `0600` assertion, which Linux CI executes.
- The deploy workflow remains push-to-`main` only. Opening a stacked PR runs quality checks and does not deploy.

## Security review truth

- Codex Security sealed artifacts cover all four changed runtime source files with `0 findings`, complete `4/4` coverage and no deferred/open questions.
- Findings SHA-256 `b1c6fc575c75a692df9d2c8f89624037e0dc10d92241fd41b2f0ae05812f8426`; coverage SHA-256 `d39ff43f9868af9f4ede2cea814cebb9eda13735972e077fe70f6481bace5892`; manifest SHA-256 `d99306401a073de4f07b275498e09c97849778433b1906c45d24a224f7ed1491`.
- The security workbench database could not commit its terminal state: `sqlite3.OperationalError: unable to open database file` at `BEGIN IMMEDIATE`. The immutable DB row remains `running`, while the sealed files say completed. Therefore the honest gate is `CODEX_SECURITY_SCAN=INFRA_FINALIZATION_FAILED/RUNNING_WITH_SEALED_ARTIFACTS`, not a claimed completed plugin scan.
- Manual/independent review found no new injection, cross-origin request, storage, cookie, auth, role, payment, wallet, provider or data mutation surface.

## Safety counters

`PROVIDER_CALLS=0` · `PAYOS_LIVE_CALLS=0` · `TELEGRAM_LIVE_CALLS=0` · `PRODUCTION_WALLET_MUTATIONS=0` · `PRODUCTION_DATA_MUTATIONS=0` · `ENV_MUTATIONS=0` · `COMMIT_AT_CAPTURE=NO` · `PUSH_AT_CAPTURE=NO` · `MERGE=NO` · `DEPLOY=NO` · `SIGNED_PRODUCTION_LIVE=NOT_TESTED`.
