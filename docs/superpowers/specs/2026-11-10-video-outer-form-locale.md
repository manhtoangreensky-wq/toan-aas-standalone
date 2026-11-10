# Video outer-form locale — combined batch, 10/11/2026

BASE_SHA=3e6732446a89ce84ddc90711294b6e504bc593b8.
Branch: codex/video-planner-outer-locale-20261110.
Tracker: Issue #689, manhtoangreensky-wq/toan-aas-standalone.

PR705 is merged/deployed and protected. This batch changes fixed presentation
copy around its two planning routes, not their actions, inputs, results or saved
confirmation. The selected public functions are byte-identical to the older
public b5410b5e snapshot used in the three immutable worker packets.

## Work queue

| Spec | Allowed application scope | Measurable outcome | Dependency/status |
|---|---|---|---|
| VIDEO-MOTION-OUTER-LOCALE | renderCreativeMotionGuide; five fixed strings in synchronizeCreativeMotionGuideForm; new videoMotionFormUi catalog |57fixed keys in VI/EN/ZH; counts/topic data escaped; current native controls, guards and selected-name scheduler unchanged | Worker running; notes need metadata catalog |
| VIDEO-ROADMAP-OUTER-LOCALE | longFormRoadmapFields/renderLongFormPlanner; new videoRoadmapFormUi catalog |66keys; all10field contracts/options/defaults/actions unchanged; labels resolve at render time | Worker running; notes need metadata catalog |
| VIDEO-PLANNING-OUTER-METADATA | Exact route-specific prefixes in localizedPageTitle/localizedPageDescription; new videoPlanningMetaUi catalog |9title/description/note keys; unrelated routes and shared signatures unchanged | Worker running |

Only `static/portal/portal.js` and `static/portal/portal-i18n.js` are allowed for
application changes. No global helper refactor, route factory/signature change,
integration/backend/auth/Bot/provider/wallet/PayOS/schema/ENV/data modification.
Each worker is output-only in its isolated public-source packet; coordinator
applies sequentially after all return. No repository-write or Git/VPS authority
is delegated.
Native prerequisite amendment: `static/portal/integration.js` may add only a
private motion-guide actor-id snapshot from the already current signed hydrate
response, cleared synchronously before hydration awaits and assigned just before
the valid signed bootstrap merge for the enabled motion route. The two motion
actions and their existing response fence use it instead of absent base.account.
Keep all epoch, route, session, feature, capability and server checks. Do not add
global account state, change auth authority or alter other product consumers.
R2 contract correction: the public browser account metadata deliberately omits
the internal id. The private ownership stamp therefore uses the existing current
signed `me.csrf_token` value in memory, not an account id, email or DOM value.
No auth API/credential/schema change, persistence/logging or new transmission.
Rename only local motion stamp/parameter/captures; preserve every fail-closed gate.
The original id-bearing test fixture was invalid and must be corrected, not used
to claim native success or count the exact R1 worker output as code failure.
Test/CI allowance: add one portable real-renderer test and one focused invocation
in the existing CI step; exclude only the three approved new namespaces from the
prior frozen original-catalog snapshot, retaining its old counts/hashes and all
prior result/copy/guard assertions. No broad test relaxation or workflow redesign.
Roadmap native readability prerequisite allows only three CSS rules in
`static/portal/portal-theme.css`: editable16px at<=620px, light label ink, light
field-help/form-note muted. Native pilot measured26unique failures (10font,
10labels,6help/note); no geometry/action change is allowed. Desktop font/dark
colors/buttons/other forms remain protected. Only affected native gates rerun.
Final combined24:allfunctional/copy states pass;18overall pass,6motion-light
contrast-only failures. Permit only two extra light motion colors: muted for
form notes and ink for stale suggestion notes, both existing tokens. Preserve
dark/roadmap18passed cases and rerun only affectedVI/EN/ZH x320/1440light six.
Two legacy Vietnamese source-copy expectations in
`tests/test_creative_motion_guide_portal_contracts.py` may be updated to the
reviewed localized fallback/key while preserving private-route and hidden-stale-
card assertions. Their old literal failures are intentional copy changes, not
accepted baseline failures or a reason to restore mixed-language text.

## Exact implementation boundaries

- Preserve every action/route/capability/data/ARIA attribute and option scalar,
  selected/disabled branch, field validation property, typed draft and generated
  record. No translation of customer/server text or change to the69result keys,
  26option/receipt keys, selected-name helper, CSS or confirmed-plan flow.
- Motion set caption is a whole `{count}`/`{topic}` phrase with correct Chinese
  order. Interpolate raw scalar/text parameters, then HTML-escape exactly once.
- Roadmap keeps the literal `longvideo` code node; fixed text before/after is
  translated and escaped separately, not injected HTML. The course scalar remains
  `course`, with concise reviewed UI label Online course/Khóa học trực tuyến/在线课程.
- Use existing `renderNotes(page, labels)` locally. Metadata worker owns the common
  title and route-note catalog. Do not change shared renderNotes implementation.
- Strict raw-data normalization, guard/confirmation semantics and NoTransient
  behavior remain unchanged. No filler cards, placeholders or fabricated results.

## One combined acceptance checklist

- [x] Baseline15real-normalizer checks executed:6protected control/data checks
  pass,9scoped fixed-copy/metadata checks fail acrossVI/EN/ZH.
- [x] All three outputs contain complete applicable code within exact allowlists.
- [x] Scoped copy in ready/guarded/custom/three-suggestion/stale states uses the
  selected interface locale; dynamic values and topology are unchanged.
- [x] Title/description/notes and accessible labels are correct; no generic
  cross-language fixed UI remains in the scoped renderers/sync strings.
- [x] One combined real-renderer/native keyboard/layout/state verification and
  proportionate regression on the stable batch. Do not run it per partial output.
- [x] Independent findings, if any, return to the same spec; rerun only required
  gates after a new patch, not unchanged source.
- [ ] Operations/tester/provenance, CI, merge, deploy and runtime reconciliation.

Exact rows/OLD code and required output schema are in the isolated packets;
GitHub contract comment6759517114 records the public scope and combined gate.
Only public source/spec/full MAP was sent; no test/API/login/fixture/customer or
credential data. No paid provider or product write was used for baseline.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
Whole-app locale, density, signed lifecycle and final motion remain in the master
ledger; this spec does not redefine the goal around only these two routes.

Native finding: an actual valid suggest action sent no request because account.id
was absent in UI state while the signed feature/session/capability flags were
true. The exact existing fence predicate was identified; no fake API request or
fixture success substitutes for repair. The original matrix is incomplete and
is not counted as24PASS. Native pilot and private-snapshot negative/stale-session
regression must pass before resuming remaining cases.

## Accepted local evidence

132new keys exactly match reviewed copy;9361prior values per locale remain
unchanged. Portable renderer24/24and full unchanged-copy Node2280/2280 pass.
After the narrow integration prerequisite,9faithful no-id hydrate/action cases
and192affected integration consumers pass; no full unchanged suite repeated.
Python22unchanged cases plus2updated literal expectations pass; one unrelated
historical mobile-nav literal remains BASE-equivalent. Native24unique cases are
accepted using18retained records plus6affected light cases; actual text-only
three-suggestion POSTs and clearly synthetic read-only stale-guide states are
distinguished. Final contrast8.4502stale/5.7971notes; no scoped readability or
functional failure remains. Delivery and whole-goal gates are still separate.
