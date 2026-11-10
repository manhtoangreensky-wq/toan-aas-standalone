# REMAINING-PLANNER-FLOW-PREREQUISITE — preserve verified metadata

BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe; Issue #689.
Baseline prerequisite found before locale application, not worker copyfailure.
Actual pure Script/Cinematic/Storyboard composers produced valid full response
shapes, no network/DB/provider/wallet/production writes. Renderer24casebaseline
18pass/6fail:Script validresult/savecontrol/receipt missing; Storyboard saved
receipt missing and duplicate save button reappears. Integration3receiptparsers
return compact objects which Portal rejects when checked as transport again.

## Exact safe alternative, no guard removal

- Portal `normalizeScriptToScreenPlannerResult`: retain only known execution/
 false metadata fields already checked by its boundaryOk, alongside existing
 sanitized planner. No raw spread, unchecked field/defaultfalse/fakeflag.
- Portal three receipt normalizers (Script/Cinematic/Storyboard): after strict
 checks retain full bounded verified content-free transport metadata so all
 existing renderer/source-matcher normalizer calls can remain intact. For
 Script add closed-key/plan-key validation using exactly existing integration
 receipt schema before returning. Other exact-key/falseflag checks unchanged.
- Integration three strict receipt parsers: success return retains full already
 verified bounded transport with normalized plan; ALL exact-key/flag/identity/
 count/state/revision checks stay. No arbitrary/private/customer fields forwarded.
- Renderer/body/source-match/normalizer signatures and calls, alreadySaved,
 permission/auth/CSRF/idempotency/requests/sourcechoices all unchanged. Never
 repeat the rejected PR708 guard-removal variant.

Allowedappfiles:portal.js7private boundary functions atmost (4Portal/3integration),
integration.js3parsers; targetedtests/fixture/spec/docs/provenance. No backend,
engine/Bot/provider/wallet/PayOS/ENV/schema/data/route/authauthority changes.
Copy workers remain separate and their results are retained, not called again
to fix this flow issue. Scope/risk is UI transport integrity, not provider execution.

- [x] Realpurecomposer shapes and24renderer cases measured beforepatch.
- [x] Integration->Portal stricttransport and allfalseflags/missing/extra/ID cases.
- [x] One Antigravity patch, exact allowlist/protected source and affected tests.
- [x] Actual signedlocal UI compose-confirm-save-readback-open for3routes,
 repeat-save terminal behavior; no paidprovider or production job.
- [ ] Retain unchanged locale/form/native evidence, only affected reruns; then
 one combined delivery after current batch gates pass. No whole-goal closure.

Commands:node --test tests/remaining-planner-current-flow.test.mjs
tests/remaining-planner-receipt-transport.test.mjs. Fixtures are synthetic output
from real pure functions, not proof savedIDs actually persisted. Native QA must
produce/read its own private temporary plans. PROVIDER_CALLS=0;WALLET_MUTATIONS=0.
