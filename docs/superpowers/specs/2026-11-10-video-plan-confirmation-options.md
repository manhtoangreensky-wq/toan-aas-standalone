# Video plan confirmation and motion options — 10/11/2026

BASE_SHA=b5410b5e587337f0d050e70d1a92fcaff85adc17.
Tracker: Issue #689 in manhtoangreensky-wq/toan-aas-standalone.
Branch: codex/video-plan-confirmation-20261110.

PR #704 is merged and deployed. Its result renderers, 69 catalog keys and scoped
mobile wrapping rule are protected. This next release does not reopen motion,
auth authority, backend persistence, provider, wallet, payments or data policy.

## Ordered units and immutable boundaries

| Spec | Outcome | Dependency | Current evidence |
|---|---|---|---|
| VIDEO-MOTION-OPTIONS-LOCALE | Resolve 19 fixed option labels at render time in VI/EN/ZH | Independent renderer tests | R1 proposed code passes 15 UI cases but inherited-property fallback fails; same-worker R2 requested |
| VIDEO-ROADMAP-SAVE-RECEIPT | Show an already validated saved-plan confirmation and safe plan link in VI/EN/ZH | Executed integration→Portal path and real owned-QA compose/save/read-back | Renderer-only R1 passes 60 source-render cases but misses integration compact-data rejection; same-spec amendment requested |
| VIDEO-PLAN-CONFIRMATION-VERIFY | Real controls, transport guards, output, no regression | Both accepted patches and functional pilot | Open |
| VIDEO-PLAN-CONFIRMATION-DELIVERY | CI, merge, deploy and actual runtime reconciliation | Full local and independent gates | Open |

Two output-only worker packets are isolated; only the coordinator applies code,
sequentially. No application repair by the coordinator before two same-acceptance
code failures. Missing contract coverage is a coordinator spec gap, not a worker
failure. The current receipt gap is recorded under the same spec, not renamed.

## Allowed files and minimal changes

- `static/portal/portal.js`: only `creativeMotionGuideOptions` and
  `renderLongFormRoadmapSaveReceipt`.
  - Map fixed labels at render time, not when frozen options are initialized.
    Use an own-property lookup; preserve unexpected labels through safe escaping.
  - The receipt renderer consumes the already normalized compact projection;
    retain its no-plan branch, encoded plan path, data/scalars and markup.
- `static/portal/portal-i18n.js`: add 19 `videoMotionOptionsUi` and seven
  `videoRoadmapReceiptUi` keys. Every existing entry remains unchanged.
- `static/portal/integration.js`: only the successful saved-receipt merge property
  in `long-form-roadmap-save-plan`: pass the already validated full `result.data`
  so the strict bootstrap validator can project it once. Keep the validation,
  failure branch, capability/session checks and submission/idempotency intact.
  Native prerequisite amendment: only the result safety scan's `character_bible`
  argument may exclude the exact canonical server-authored negative guard
  sentence. No generic negation/prefix exception, input guard, original pattern,
  schema or other field scan may change. Unsafe variants must remain rejected.
- Focused new tests, one invocation in the existing CI locale step, this spec and
  corresponding operational/tester/ledger/provenance evidence.
  Existing `video-planning-result-locale.test.mjs` catalog comparator may exclude
  only the two approved new namespaces from its original catalog snapshot;
  keep its original counts, hashes and all 69 prior-result copy checks unchanged.
- `static/portal/portal-theme.css`: one appended `max-width:620px` font-size16px
  rule scoped to the motion compose form's editable controls; native baseline
  found three selects and one textarea at13px. Buttons/desktop/other forms stay
  unchanged; native control/keyboard/layout checks remain required.
  Visual amendment: one mobile select width constraint (min-width0, width/max100%)
  and two light-only label/help color rules using existing ink/muted tokens.
  Native measured363px control in292px field and light text contrast1.265:1;
  require actual control containment and normal-text contrast4.5:1, not merely
  page overflow=false. Dark colors, font16 and full option labels stay unchanged.
  Strengthened visual follow-up: extend select containment to all widths and
  add a private coalesced-frame selected-name helper with one sync call and
  resize/font-ready hooks. Show a plain wrapped aria-hidden name only when the
  native selected text cannot fit; remove it entirely when it fits. No empty
  hint/card, native control replacement, payload change or persistent form state.

Do not change shared merge, strict normalizers, API routes, backend persistence,
ownership, auth/CSRF, provider, wallet/PayOS, schemas, ENV or credentials. Do not
fake success or add fallback saved data. Do not translate user/server text.

## Acceptance checklist

- [x] AC-01: Three option lists retain 9/3/7 values, defaults, ordering, selected
  states and four actions; 19 fixed labels show the chosen language.
- [x] AC-02: Unknown labels, including inherited property names and HTML-like
  input, remain exact escaped visible text rather than blank labels.
- [x] AC-03: A valid 31-key receipt passes the actual integration→merge→Portal
  path and renders the localized confirmation/link with correct scalars.
- [x] AC-04: Missing/extra/unsafe or side-effect-bearing envelopes produce no
  saved confirmation; all 51 baseline rejection cases remain rejected.
- [x] AC-05: Owned native DOM compose/save/read-back proves the actual private
  plan exists and the confirmation is visible. HTTP200 alone does not pass.
- [x] AC-06: Existing result copy, CSS, controls, identifiers and prior catalog
  values are unchanged; full Node and relevant Python contracts pass or have
  explicit comparable BASE failures.
- [x] AC-07: Native VI/EN/ZH × light/dark × mobile/desktop, keyboard, safe links,
  no clipping/errors/external requests/unapproved writes; inspect screenshots.
- [ ] AC-08: Independent review, operations/tester evidence, provenance and CI
  precede merge/deploy; production signed behavior remains separately classified.

## Actual pre-build evidence

- Initial options: 15 tests, nine protected pass, six locale RED.
- Initial receipt: 60 tests, 54 protected pass, six missing-confirmation/copy RED.
- First worker candidate: 75/75 source-render cases pass. Independent review:
  0 Critical, 1 Important chain gap, 1 Minor unexpected-label fallback defect.
- The real integration receipt helper produces a compact value; passing that
  exact value through the real strict Portal normalizer drops it in all three
  locales. Direct full-envelope fixtures do not prove the integration path.
- Existing backend tests in isolated temporary storage: 5/5 pass, including
  private persistence, idempotent replay and no-provider/no-wallet boundaries.
- Initial actual DOM compose pilot: safe server response, but result heading not
  observed before timeout. No save request was sent. Further bounded DOM/source
  capture must classify this before any functional success claim.
- The bounded capture and executed real validator subsequently proved the
  server's fixed negative `không mô phỏng người...` instruction is itself matched
  by the originality pattern. This result-only exact-sentence prerequisite is
  added under the same spec; it is not an excuse to weaken input validation.

PROVIDER_CALLS=0. WALLET_MUTATIONS=0. PRODUCTION_DATA_MUTATIONS=0.
Temporary QA writes are restricted to owned test account setup, text-only compose
and private plan save in a disposable database. No production login or mutation.

## Local acceptance record

The final stable batch passed332focused and2256fullNode tests, native motion24/24
and real native compose/save/open12/12. Independent code acceptance has no
Critical/Important finding in the declared scope. The report records exact
guard/line/ARIA/geometry/contrast conditions and partial-run/harness corrections.
One older empty-topic observation remains unexplained (not reproduced in the
final120FormData snapshots); two pre-click overlap positions remain recorded.
Neither is silently labeled fixed. CI/delivery and whole-goal audit stay open.
