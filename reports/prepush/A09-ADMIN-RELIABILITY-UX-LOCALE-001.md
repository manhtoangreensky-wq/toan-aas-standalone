# A09 — Reliability Admin UX and locale

Spec: `A09-ADMIN-RELIABILITY-UX-LOCALE`
Route: `/admin/reliability`
Branch: `fix/a09-admin-reliability-locale`
Base: `cc68747f216755c3e4808dbe2e3bf67d94ed9a41`

## User-visible change

The page is task-first: “Items to review/Việc cần kiểm tra” and its filters are
shown before metrics and signals. Operational and permission explanations live
in one keyboard-accessible disclosure, closed initially. The disabled state is a
single concise status surface with a safe return to the Admin center; it does not
claim that the account lacks permission. Fixed copy is locale-specific for VI,
EN and ZH; record IDs, state values, revisions and action names remain canonical.

## Measured verification

- Enabled local QA: 20 states (VI/EN × light/dark × 1440/1024/768/390/360).
- Disabled local QA: 8 states (VI/EN × light/dark × 1440/390).
- Both reports: page overflow `0`, clipped labels `0`, relevant console events `0`,
  Reliability write requests `0`, framework overlay `0`, touch-target violations `0`.
- Enabled minimum sampled text contrast: `5.8:1`.
- Enabled metrics: 4 columns at desktop, 2 columns at tablet/mobile.
- Disabled status surface width: `760px` desktop and `358px` at 390px; nested
  card/state count `0`.
- Keyboard interaction: disclosure opened and closed with Enter in the local QA
  script; filter selection remained read-only.

Evidence files (task-root, intentionally outside public repository):

- `evidence/a09-admin-reliability-ux-20260911/browser/a09-reliability-ux-browser-qa.json`
- `evidence/a09-admin-reliability-ux-20260911/browser-disabled/a09-reliability-disabled-browser-qa.json`

Latest report SHA-256 (after final source changes): enabled
`A3EB70CC1BFEB50825FCB1C8BB1A11F4DDFC42B51132DED849725F5B94F41FA7`, disabled
`77B95DAC562D71F9405A70692D912F2E66503ADC5EA683E4D8B9D0DD6D270288`.

## Code and safety review

- Changed surfaces: `static/portal/integration.js`, `static/portal/portal.js`,
  `static/portal/portal-i18n.js`, `static/portal/portal-theme.css` and their
  focused contracts; no Bot, API, schema, ENV, provider or wallet changes.
- Reliability backend contract suite: `10 passed`, one existing Pydantic warning,
  using disposable local databases.
- Final source/portal/test suite before push: `97 passed`, one Pydantic warning,
  one Windows-only POSIX permission test deselected; Linux CI must run that test.
- Protected comparator exact current base/candidate: both `68 passed / 2 failed`,
  identical baseline IDs (`test_admin_css_override_is_scoped_dense_visible_and_responsive`,
  `test_admin_home_final_hierarchy_is_scoped_balanced_and_motion_stable`),
  `NEW_FAILURES=0`.
- First PR CI `34585998814` stopped after `192 passed / 1 failed`: changing the
  Reliability CSS section comment caused the preceding Automation Monitor parser
  to consume the next section. Restored the canonical section marker. The same
  gate then exposed two intentional Reliability visual decisions; the route now
  uses semantic `--portal-app-canvas` (never literal transparent), and the mobile
  2×2 metric expectation is backed by the measured browser matrix. Focused
  Automation/Finance/Security/Reliability CSS contracts pass after correction.
- Dynamic values are HTML-escaped; malformed state/capabilities expose no action.
- Existing manager/operator capability, CSRF, confirmation, revision and
  idempotency gates are unchanged. No production action was submitted.

## Scope and limitations

This proves local rendered behavior and source contracts. It does not enable
Reliability on VPS, create follow-ups, or prove production enabled-state data.
Production read-only currently reports the feature disabled; that state must not
be changed merely to obtain an enabled screenshot. The existing CUA/IAB browser
blocked localhost, so Playwright Chromium was used with the explicit fallback
reason recorded in the evidence JSON.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_MUTATIONS=0
RELIABILITY_WRITES=0
LIVE_PASS=NOT_TESTED_FOR_CANDIDATE_ENABLED_STATE
