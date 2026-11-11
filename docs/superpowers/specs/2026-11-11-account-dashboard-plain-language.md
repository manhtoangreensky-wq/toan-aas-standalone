# Account and Dashboard — plain-language copy contract

TASK=ACCOUNT-DASHBOARD-PLAIN-LANGUAGE; BASE_SHA=8b13f094de39203771a7735e4d80d716134b63f1.
Branch=codex/account-dashboard-plain-language-20261111; product=standalone WebApp; Issue689.

Owner asks to remove irritating technical sentences and useless UI, while keeping
the real app functional. PR719 already delivered membership line-break and app/
landing accents; those CSS, membership and visual evidence are protected here.

## Locked scope and source evidence

Only the named Account profile/login/Bot-help strings, Account profile audit span,
four hardcoded provider labels in renderAccount, and redundant Dashboard assurance
details are editable in portal.js. Only 30 named keys x VI/EN/ZH are editable in
portal-i18n.js. Full existing MAP is included in every output-only worker packet.
No generic suppression/filter, blank placeholder, data rewrite, dynamic errors
hidden, capability change, auth/CSRF/backend/API/provider/wallet/PayOS/schema/ENV/
session/motion/SW/workflow change. Unrelated untracked campaign YAML is preserved.

Actual account renderer at 31313+, actual ACCOUNT_CENTER_MESSAGES catalogue at
8867+, Dashboard account/work/guarded copy at 4373+/4573+. The catalogue overrides
friendly editorBody fallback with metadata/CSRF prose: both consumers must change.
Inactive historical audit/assurance translations remain; absence from renderer,
not global key deletion, proves they are no longer shown as repeated filler.

## Ordered queue and acceptance

|Order|Spec|Result|Dependency|State|
|---|---|---|---|---|
|1|PL-ACCOUNT|Plain profile/login wording; no audit span/protocol label; same correct-account warning, consent, recovery and controls|BASE resolved|READY|
|1|PL-BOT-HELP|Plain help; exact commands/links/disable guards, explicit user handoff and separate deletion policy preserved|BASE resolved|READY|
|1|PL-DASHBOARD|Plain account/work/guarded help; remove duplicate internal assurance details; real read/error states unchanged|BASE resolved|READY|
|2|PL-VERIFY|Actual VI/EN/ZH renderer + native Account/Dashboard mobile/desktop, focus/actions/overflow/error checks|1 reviewed|WAITING|
|3|PL-SHIP|Ops/original-feature/tester/metadata/provenance, exactHEAD CI/merge/deploy/runtime/assets and receipt|2 accepted|WAITING|

Output-only workers write different packet output directories; no shared source
mutation. The coordinator alone applies reviewed exact returned edits. Same-part
two-failure rule remains; brief/harness errors never count as worker failures.

- [x] Actual source, catalogue, prior delivery and current Git identity inspected.
- [x] RED against real renderer captures technical copy, not grep-only evidence.
- [x] Worker packets self-contained, precise OLD/NEW and complete MAP; existing login.
- [x] Combined review: only allowed spans; other catalogue entries and markup/data exact.
- [x] VI/EN/ZH preserve same-Telegram/no-email-auto-merge, confirmation, code secrecy,
  manual Bot handoff, separate deletion policy, disabled actions and actionable errors.
- [x] Relevant Node/Python/syntax checks and affected isolated native views pass.
- [x] Ops/original-feature/Tester/case metadata reviewed.
- [ ] Provenance refreshed and verified after source commit before push.
- [ ] Exact finalHEAD CI, merge, exact merge deployment, runtime/service/asset evidence.
- [ ] Issue689 and PR receipt updated; broader original goal/motion remain open.

## Verification and protected comparators

`node --test tests/account-dashboard-plain-language.test.mjs` must be GREEN after
real RED; existing Account/Dashboard/control/security/billing locale suites remain
unchanged unless an exact obsolete copy assertion requires a documented amendment.
Reverse returned worker patches must restore byte-exact BASE application files.
BASE/branch controls/form attributes/disabled/confirm meanings/raw context and all
non-target catalogue entries compare equal, aside from the explicit copy allowlist.
Native flow: isolated synthetic login -> Account/Dashboard -> real hydrated copy ->
keyboard focus/profile typing without submitting -> mobile/desktop screenshots.
Only localhost QA; no signed production browser, role elevation or external login.
Owned temporary DB/input hashes and source remain unchanged; owned Job ends at0.

No call to Bot/provider/payment and no product write is needed. PROVIDER_CALLS=0;
WALLET_MUTATIONS=0. Signed production/device/Safari/all-site copy and normal motion
remain NOT_TESTED here. Whole goal is not complete when this bounded unit ships.

## Preflight measured baseline / test-only amendment

New real renderer tests:36 total,27RED/9pass before app edits. Existing Python
Account/Dashboard/security/motion source contracts:35pass/4fail at BASE. One
Account catalogue-consumer assertion still demands overviewBody/sessionSecurityBody
removed intentionally in prior PR719. Correct only its consumer set to distinguish
three retained historical-but-hidden explanations (those two plus editorAuditNote
removed here); catalogue completeness remains101keys x3locales, not weakened.
Three pre-existing dashboard-motion source assertions remain unchanged/out of
scope: reduced-rule rindex assumption and two obsolete exact mount markers.
Motion files/behavior and those three failures are protected BASE comparators,
not new regressions and not treated as solved by this copy unit.

GitHub tracking contract: Issue689 comment6788257719. PR719 merge-head CI
42966856281 completed SUCCESS at exactBASE8b13f094. No worker failure yet.

Before application, coordinator copy-safety amendment: botUnavailableBody must not
claim unrelated options are enabled, since their capabilities can differ. Keep
only retry/support guidance. Dashboard guardedBody must require both linked
Telegram and loaded account data, never imply linking alone ensures availability
or demand relinking an already linked account. Two bounded same-session amendments
replace only these two three-locale entries (and Bot fallback). Original worker
outputs remain otherwise unchanged. This is a coordinator spec correction, not a
worker implementation failure, and is included in the one combined verification.

CI/test-only allowance: append this unit's Node test and the affected existing
Account/Dashboard Python contracts to the existing presentation-regression step in
webapp-quality.yml. No trigger,permission,timeout,dependency,deploy or existing
gate change. This ensures exactHEAD CI actually runs the newly added regression.
Test harness copy checks examine rendered text and accessible title/confirm text,
not internal data-action identifiers such as link-oauth-google (kept unchanged).

Combined first review: exact returned payload and48BASE/branch renderer comparators
pass;24/36tests pass. Six account failures identify three missed existing field
help strings (displayNameHelp/localeHelp/timezoneHelp), not worker-code mistakes.
Add only those3keys x3locales and their3profile FIELD_SETS fallback expressions
(only consumer renderAccount; no factory/signature/validation change), total33keys.
Same account conversation receives this missing-spec amendment. Six Bot-policy
checks failed because the coordinator's section helper stopped at a nested section
closing tag; fix balanced section matching, no application change for that error.
Dashboard existing source test must cease requiring the two deleted assurance
consumer expressions while retaining full catalogue completeness. Motion unchanged.

## Local acceptance evidence

145Node/138Python pass;48actualBASE/branchcontrol-data/non-targetcatalogue/HTML
comparators;24nativeviews+12DOMedits+24screenshots+12profilecrops. Native actual
Dashboardguarded only,otherreadstatesrendererfixtures;normalmotion/signedLIVE/
device/whole-site remain open.0provider/wallet/productwrites/egress/.env/media;
originalDB/evidence/sourcekeep,6plan18scenequickcheck,42ownedprocesses->0.
Apppy_compile/JSsyntax/diffcheckexit0. Three existing motion failures remain same
IDs asBASE; no new failures. Account consumer-obsolescence finite amended test
retains101profilekeys x3. Tester canonicalsource1068lines123130LFbytes,metadata
hashab5a9b2e4858e8e775e2a7665cba0b66e300cf96e62d38a5e4f253dc212ee08b.
This contract freezes before provenance; exact CI/merge/deploy/runtime receipts
published on existing Issue689/PR, not guessed in source documents.

## CI historical-catalog prerequisite amendment

CI42970854202 failed three locale hashes in video-planning-result-locale after
the new39Node/24Python presentation checks passed. The historical whole-catalog
snapshot helper permits prior publishing copy changes but not these33approved
keys. Finite test-only amendment: add a literal before/approved33key fixture and
test snapshot adapter, asserting each current approved value before restoring
only that key's historical value for old hash comparisons. No golden hashes,
counts,filters or production files change. Reuse in existing customer-copy helper
and three newer direct whole-catalog snapshot tests (remaining/last-two outer/
last-two results). Test wrong approved value must still throw; unknown values pass
unchanged into original golden hash. Existing exact worker/protected/native
evidence remains valid; only affected catalog tests rerun. Coordinator harness
omission,WorkerFailures0;not authorization for runtime scope expansion.

Affected local evidence after amendment:450/450Node tests across adapter mutation
guards9 and all six legacy consumers; original golden constants/counts unchanged.
App source untouched;145initialNode/138Python/native24/48parity retained rather
than repeated. CI command also includes9adapter tests. Update exactsource/evidence
commits before finalCI; firstfailedrun preserved,not relabeled success.

CI42971816972 passed functional/source/browser gates but final whitespace check
blocked one blank EOF line in the new JSON test fixture. Remove that blank line
only; semantic JSON/application/native evidence unchanged. Verify full BASE..HEAD
diff whitespace rather than only unstaged diff. Tests excluded from runtime source
fingerprint; existing provenance still applies if finalSHA verification confirms.
