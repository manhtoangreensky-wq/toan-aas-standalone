# Saved-plan system copy — ordered implementation contract

SPEC=VIDEO-SAVED-PLAN-SYSTEM-COPY; tracker Issue #689.
BASE_SHA=7ef871e396a3f3c9d006b24397044ed68870c8cf.
Branch=codex/saved-plan-system-copy-20261111.

Goal: new Image Motion and Reference Format plans retain useful, correctly
localized editing notes when saved and reopened, without repeated internal
explanations or an invented audience. Content language is not UI language.

Root cause: the composers already localize system prose, but the two pure
save converters hardcode English headers and paragraphs. Reference objective
also reads a Vietnamese-only global goal direction. This is not a provider
or rendering-engine fault. Existing/customer records are never rewritten.

## Locked scope and decisions

Allowed application edits: exactly the two `_..._planner_to_video_plan`
functions in `copyfast_video_studio.py`, and new data leaves under each
existing dictionary in `copyfast_video_output_copy.py`. No other application
code, imports, schemas, helpers, compose/save callers or field limits change.
Test delivery additionally allows one invocation of the new test module in
`.github/workflows/webapp-quality.yml`; deployment workflow is protected.

Image fixed copy follows the existing exact vi/en/zh content-language selector
(strip/lower, unknown -> VI system-copy fallback only). Raw stored language
remains unchanged. Reference keeps existing vi/en validation, with localized
goal direction from the already-reviewed output-copy table. No zh schema change.

New Image audience is the existing optional empty value, not the meaningless
"Private Web editor". No customer audience is inferred. Reference audience
remains exactly the customer's value. Image objective is a useful image-motion
goal. Brief retains source name and selected settings, plus one concise true
statement that the editing plan has not created a video. Remove repeated
"private editable plan" introductions and execution disclaimers in every scene.
Scene notes retain timing, camera, audio and editorial values with localized
headers. Scene-title system prefix never exceeds original English `Scene `.
Customer values are interpolated once; literal braces are not rescanned.

Protected: customer/source text, old records, title limits, timing, IDs, ratios,
tags, scene roles, narration/on-screen-text defaults, rights/claim flags,
schema/auth/CSRF/session/DB/ENV/provider/wallet/PayOS/Bot/route-engine/motion,
frontend and deployment workflow. No production writes or paid-provider calls.

## Ordered checklist / evidence gate

| Order | Spec | Dependency | Run / measurable acceptance | Status |
|---|---|---|---|---|
| 1 | SAVE-IMAGE-COPY | deployed PR715 | New saved fields VI/EN/ZH, real customer/source values preserved, no invented audience | LOCAL_GATE_PASS |
| 1 | SAVE-REFERENCE-COPY | deployed PR715 | New saved fields VI/EN, goal direction localized, real audience preserved | LOCAL_GATE_PASS_R2 |
| 2 | SAVE-COPY-ACCEPTANCE | both workers | One combined source/data review, targeted pure tests and zero new boundary rejections | LOCAL_GATE_PASS |
| 3 | SAVE-COPY-NATIVE | local acceptance | Actual compose-confirm-save-GET-reopen flows, real temporary DB, mobile/desktop | LOCAL_GATE_PASS |
| 4 | SAVE-COPY-SHIP | native accepted | Ops/original-feature/tester/provenance, exact-HEAD CI/merge, exact-merge deploy/runtime/assets | WAITING |

- [x] Coordinator RED: real converters, all supported content languages and choices.
- [x] Two independent output-only Antigravity sessions; no shared mutable files.
- [x] Full returned functions and17new copy leaves match exact packet plus one R2 EN value.
- [x] Pure language/customer/structure/length gates:15retained+3affectedpass.
- [x] BASE comparator:40cases,0newrejection;2BASE-equivalentrejections retained.
- [x] Six actual signed localhost flows save/read back/reopen localized values;
  12views/6plan18scene/36screens, no API result stubs. Actual opened views light.
- [x] Dark supplement:6already-saved plan views, actual toggle/DOM/computed
  palette proof;0compose/0save,282label samples min5.522477721172796:1.
- [x] Sensitive files and all other application text outside two function spans unchanged.
- [x] Ops/original-feature/tester and Web-only source provenance ready before push:
  source f5ab4e3248f06dd406d33a38234bc1b4d14ab3e8,
  fingerprint83308074cb7e6fc8617087cd5aa1db8d604a41556fcba81cfc98032980ce8d99.
- [ ] CI/exact HEAD merge/deploy/runtime/assets have separate receipts.

Each packet includes current source anchors, exact target requirements, complete
MAP.md, verify command (coordinator runs), protected paths and stop conditions.
Worker round1 -> same-spec correction round2 only if acceptance fails; no direct
coordinator application implementation before two genuine worker failures.
No re-running unchanged suites after a scoped correction. No screenshot/UI cache
assumptions. The full goal and next saved-detail UI/clutter/old-record presentation,
11 BASE-equivalent title-boundary rejections, other locale/AX/auth/device/live
requirements and motion-last remain open. This spec cannot close the full goal.

TESTS: `python -m pytest --noconftest -q tests/test_saved_video_plan_system_copy.py`
must pass all saved-output checks after implementation; source and native gates
are separate. `PROVIDER_CALLS=0; WALLET_MUTATIONS=0; AUTO_PROMOTION=OFF`.

Preflight test correction before dispatch: the existing middle scene role is
`problem`, not `product`. Coordinator corrected that mistaken test expectation;
the helper/application remains unchanged. This is not a worker failure.

## Same-spec R2 copy amendment before release

R1 outputs matched both exact functions and17new data leaves; source comparator
proved all other module text/134existing leaves/16protected paths unchanged.
Combined18-test group:15passed/3failed. English Reference brief label
`Reference file: {p0}.` accidentally contains the existing forbidden URL marker
`file:`; the40-case comparator found7new EN rejections. Coordinator prescribed
the bad label; this is a spec omission, not a worker implementation failure.
R2 changes exactly that one EN value to `Selected video: {p0}.`, preserving all
other50new locale values,402original values, functions/customer data and guards.
Release remains locked until3failed tests and boundary gate pass, then native.

R2 exact one-value output accepted;3affectedtests passed,15unchanged passed
evidence retained.40boundarycases now0newrejections/2BASE-equivalentrejections.
Native persistence passed12views/6actualflows/6plans18scenes and versions,
222reopenedformfieldcomparisons,quick_checkok,48ownedJobprocesses->0. Visual
inspection found the driver labelled dark from URL although opened views were
light. No application regression inferred. Add six read-only actual-dark views
on a copy of the owned QA database; preserve evidence and no save replay.

Dark supplement passed6actualGET/reopenedviews; real root/body flags and computed
root/body/editor background luminance0.007113/0.012117/0.021983 all below0.18.
Plan/scene content hash and counts6/18 unchanged; original evidence unchanged,
quick_checkok,22ownedJobprocesses->0. No persistence flow was repeated. Snapshot
at source commit; final CI/merge/deploy/runtime receipt in Issue689 is delivery truth.

## CI dependency amendment — generated Tester metadata only

CI42894662374 atHEAD32aaa9a7 passed the saved-copy stage but stopped at
`test_readiness_json_has_explicit_truth_and_file_metadata`:294critical tests
passed,1failed because canonical case source now1024lines/118779bytes, whereas
`reports/migration/p0-05d-tester-workspace.json` records1013lines/117256bytes.
This is coordinator Tester-metadata maintenance omitted from the pre-push gate,
not an application/worker failure. Allow exactly that generated JSON dependency:
refresh only the changed canonical-file lines/bytes/SHA plus local refresh date/
scope; preserve every historical remote/P0/48case/financial/safety field. Do not
change tests, app, workflows or other source. Rerun the one failed metadata test
locally, retain all18local/native evidence, then exact newHEADCI on samePR716.
Source fingerprint remains unchanged because this dependency is audit output.
