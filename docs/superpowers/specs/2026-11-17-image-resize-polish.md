# IMAGE-RESIZE-POLISH-20261117 — ordered UI contract

Product: standalone WebApp; tracker Issue #689.
BASE_SHA=93b41f523f2811b8934a61e4b4db8681572ad14c, delivered PR757.
Branch: codex/image-resize-polish-20261117.

Three returned Antigravity Gemini3.8FlashHigh R1 proposals retain their
individual acceptance: IMAGE-RESIZE-OUTER-META (five edits),
IMAGE-RESIZE-LIGHT-CONTRAST (one edit/two foreground selectors), and
IMAGE-RESIZE-REMOVE-TECHNICAL-FOOTER (one complete section removal).
No new worker call or coordinator-authored application repair.

## Scope and immutable domains

Allowed application files: copyfast_pages.py, static/portal/portal.js,
static/portal/portal-i18n.js, static/portal/portal-theme.css. Exactly the seven
literal replacements in tests/fixtures/image-resize-polish-reviewed.json.
No signatures, routes, forms, rights, inputs, native selects, action/loader
guards, customer names, output handling, dark styles, font, geometry or motion
may change outside those pairs.

Protected: all other Python, integration.js, portal.css, auth/session/CSRF,
engine/Bot/provider, wallet/PayOS/price, ENV/secrets, DB/schema, production
data, CI/deploy behavior and Owner's unrelated untracked state.
No external/provider call or product submission in local QA.

Allowed verification/docs files: one fixture, portable behavioral test,
finite historical snapshot helper, pure server-shell test, and narrowly
affected historical test read boundaries. Old hashes/assertions stay literal.
Historical readers may remove only the seven reviewed changes; new behavior
must run physical source directly. No broad masks, skipped tests or fake UI.

## Observable acceptance/checklist

- [x] Dependency PR757 actually delivered; merge/runtime/source tree matched,
  deploy44074756251 succeeded and readonly runtime/asset checks passed.
- [x] Three proposals returned exact; reviewed once; zero worker code failures.
- [x] Client preparation measured nine expected RED cases in1287.7261ms.
  Same delivered application bytes; do not repeat those baseline cases.
- [x] Actual owned BASE records six VI/EN/ZH ×375light/1440dark cases,
  first HTML/bootstrap/header/hero, complete footer and real label/help paints.
- [x] Serial replay exactly seven changes; numerical GREEN light label/help
  contrast at least4.5:1, unsupported paint cannot be treated as PASS.
- [x] GREEN outer title/description matches literal VI/EN/ZH metadata from
  the fixture and complete final notice/notes section is absent, no empty box.
- [x] Original five fields/source options, actual image selection,1080×1920,
  Tab order, actions/history/customer text remain. No product submit.
- [x] One affected portable group plus pure server shell; only affected
  failures rerun. Non-ready states/outside routes preserved.
- [x] BASE/GREEN native comparisons preserve dark paint, font/control geometry,
  source bindings and exact temporary DB/audit evidence; owned active0.
- [x] Full diff/protected review, current operations/original feature
  comparison and Tester READY before push.
- [ ] Exact-head CI, guarded merge/equal tested tree/exclusive exact-SHA
  deploy/runtime/services/assets and Issue689 final receipt.

Native limits: startup60s, group180s, action10s, cleanup5s. Fresh three
registrations/three logins/twelve metadata rows/no blobs per phase, fake
child-only QA session secret, no prior accounts or raw evidence reuse.
Browser plugin not available; use established owned Playwright/Chrome path.
Signed production UI/device/Safari/final PNG and whole-goal/motion acceptance
are separate and must not be inferred from this unit.

Next new twelve-row Resize copy and Compress metadata proposals stay queued,
NOT_APPLIED. Separate connection analysis does not authorize engine changes.
PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.

Actual evidence:one35file679NodePASS115005.6486ms,server12PASS3.34s+
9ChatPASS2.32s;nativeBASE6/GREEN6/30lighttargets/30darkpairs/30controlpairs.
Light1.265330–2.021153→5.797099–12.351555:1;140protected application
source files exact;CI adds only two commands. Exact-head CI/delivery remain open.
