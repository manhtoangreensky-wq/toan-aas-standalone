# VIDEO-USEFUL-UI — remove redundant video planner blocks

BASE_SHA=5ad97cf9de90a1d5caa3b8e70c9e2555d37bf466; Issue #689.
Branch:codex/video-useful-ui-20261110. PR709 is deployed and protected; current
task extends Owner's screenshot request to the next bounded nonoperational UI.

Three isolated Antigravity tasks cover only renderVideoPromptPlanner,
renderVideoIdeaPlanner and renderSelfShotScenePlanner. Each removes the intro
boilerplate/zero-call metrics, static execution-boundary aside and final
scope/notes section. Only the outer two-column wrapper becomes existing
portal-stack, preventing an empty second column. No new CSS or copy namespace.

After native visual review, remove one technical form-header paragraph per route
explaining signed-session/CSRF/template/storage internals. These nodes are outside
the actual forms. This removes redundant explanation, not authentication checks.
Every form/control/input help/consent/default/action/disabled attribute remains
byte-identical; result/save calls/arguments/order/capability expressions stay.

| Gate | Required evidence | State |
|---|---|---|
|Baseline|6renderer cases3pass/3redundant-blockRED|Measured |
|Threeworkeroutputs|Exact4hunks each; syntax; formSHA unchanged|Accepted |
|IdeaR2|Same3OLDanchors still added one space before closing paragraph|After2same failures, coordinator corrects only3OLDanchor spaces; NEW code unchanged |
|Combinedrenderer|6/6pass; no intro/aside/scope or blank secondcolumn|Accepted |
|Nativeinitial|3routes x320dark/1440light VI, input/focus/font/labels/width/overflow/errors|6/6accepted, GET-only after one QA login |
|Technicalsubtitleamendment|Exactly3paragraphremovals outsideform|Worker output matched/applied |
|Finalaffectedgate|6renderer/6affectednativeinitialviews;formhash/resultcalls/12protectedpaths/allotherportalbytesunchanged|Accepted |
|Delivery|Ops/featurecomparison/tester/provenance/CI/merge/deploy/runtimeassets|Open |

No current PR or worker writes to the repository while running; coordinator
applies sequentially. File allowlist:static/portal/portal.js (three outer
functions), targeted test/CI and scoped docs/provenance only. CSS/i18n/inner
field/result/save/normalizer/integration/auth/route/backend/engine/Bot/provider/
wallet/PayOS/ENV/schema/customer/production data remain protected.

The three formSHA256 are recorded in local packet contracts and source review.
Existing9actualsaveflows/99unit/74contrast evidence is retained because every
form/result/save/control/guard is unchanged. No duplicate tester/whole-suite run.
Only user-visible narrative/layout changes get a focused native gate.
This is not adding media generation, not hiding real error or task output, and
not whole-app completion. Remaining routes/template locale/AX/auth/motion stay.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
