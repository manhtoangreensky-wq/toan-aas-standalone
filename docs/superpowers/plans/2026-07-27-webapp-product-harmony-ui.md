# Web App Product Harmony UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the standalone signed Workspace and Admin ERP into one clean teal–sky product system, with Vietnamese-first three-locale fixed copy, while retaining all existing authority and workflow boundaries.

**Architecture:** `static/portal/portal-theme.css` remains the final visual layer over the legacy catalogue: it owns semantic colour and layout overrides while `portal.css` retains component behaviour. `portal.js` changes only fixed presentation markup/copy in the Admin overview; all access, data hydration, API, CSRF, payment, provider, Bot and PWA behaviour remains unchanged. The public `toanaas.vn` landing is intentionally a separate repository/PR after this Web App PR lands.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript, semantic CSS tokens, existing portal i18n catalogue, pytest static contracts, Browser visual smoke testing.

---

### Task 1: Lock the visual and authority boundaries with a focused contract

**Files:**
- Create: `tests/test_product_harmony_ui_contracts.py`
- Read: `docs/superpowers/specs/2026-07-27-product-harmony-teal-sky-design.md`
- Read: `static/portal/portal-theme.css`
- Read: `static/portal/portal.js`
- Read: `static/portal/portal-i18n.js`

- [ ] **Step 1: Write the failing visual-system contract**

```python
def test_product_harmony_uses_the_canonical_teal_sky_tokens_and_light_operational_surfaces() -> None:
    for token in (
        "--portal-rail-width: 272px;",
        "--portal-content-max-width: 1600px;",
        "--portal-mobile-content-inset: 104px;",
        "--portal-action: #0f766e;",
        "--portal-context: #0284c7;",
    ):
        assert token in THEME
    assert "linear-gradient" not in product_harmony_css()
```

```python
def test_admin_overview_is_fixed_copy_with_svg_not_an_emoji_or_browser_authority() -> None:
    overview = section(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship")
    assert 'portalIcon(ICONS.security)' in overview
    assert 'aria-hidden="true">⌘</span>' not in overview
    assert "adminHome.title" in overview
    for key in ADMIN_HOME_KEYS:
        assert I18N.count(f'"{key}"') == 3
```

- [ ] **Step 2: Run the focused contract to verify it fails**

Run:

```powershell
$py = 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pytest -q tests/test_product_harmony_ui_contracts.py -p no:cacheprovider
```

Expected: FAIL because the canonical layout variables, Admin fixed-copy keys and final light ERP overrides do not exist yet.

- [ ] **Step 3: Keep the red contract uncommitted until Task 2 makes it pass**

The branch must never publish a failing implementation commit. The test stays
in the worktree as the regression proof for Task 2.

### Task 2: Introduce semantic geometry and repair light-surface imbalance

**Files:**
- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_product_harmony_ui_contracts.py`
- Regression: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Regression: `tests/test_app_first_ui_system_contracts.py`

- [ ] **Step 1: Add final-layer geometry aliases in `:root`**

Add only semantic variables inside the existing root block:

```css
--portal-rail-width: 272px;
--portal-content-max-width: 1600px;
--portal-desktop-page-padding: clamp(24px, 3vw, 40px);
--portal-mobile-page-padding: 16px;
--portal-mobile-content-inset: 104px;
--portal-section-gap: clamp(20px, 2.4vw, 30px);
```

Do not introduce a hex literal outside `:root`; use the existing
`--portal-*` colours in every new declaration.

- [ ] **Step 2: Make shell alignment consume those tokens**

Replace only the final theme layer’s corresponding values with the aliases:

```css
.portal-shell:not(.portal-shell--auth):not(.portal-shell--landing) {
  grid-template-columns: var(--portal-rail-width) minmax(0, 1fr);
}
.portal-main {
  width: min(100%, var(--portal-content-max-width));
  max-width: var(--portal-content-max-width);
  padding: var(--portal-desktop-page-padding);
}
```

On mobile use the 16px semantic page padding and
`var(--portal-mobile-content-inset)` so content clears the dock. Preserve the
existing `safe-area` calculations and all focus/reduced-motion rules.

- [ ] **Step 3: Add final light-surface remediation for known legacy cards**

Scope overrides to the signed application and target the dark legacy
components that currently make otherwise light screens look mismatched:

```css
.portal-shell:not(.portal-shell--auth):not(.portal-shell--landing) :is(
  .portal-workspace-setup-focus-card,
  .portal-workspace-setup-focus-icon,
  .portal-workspace-menu-group-head > span
) {
  border-color: var(--portal-border);
  background: var(--portal-surface-light);
  color: var(--portal-ink);
}
```

Use more-specific child rules for checked, hover and focus states so they use
`--portal-surface-soft`, `--portal-border-strong` and `--portal-context`;
do not change form state, input values or event handlers.

- [ ] **Step 4: Run the theme regressions**

Run:

```powershell
& $py -m pytest -q tests/test_product_harmony_ui_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_app_first_ui_system_contracts.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit the shared surface slice**

```powershell
git add static/portal/portal-theme.css tests/test_product_harmony_ui_contracts.py
git commit -m "feat: align teal sky workspace surfaces"
```

### Task 3: Make the customer dashboard balanced at desktop and mobile

**Files:**
- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_dashboard_workspace_command_center_contracts.py`
- Modify: `tests/test_product_harmony_ui_contracts.py`

- [ ] **Step 1: Extend the contract for an even small-screen summary**

```python
def test_dashboard_keeps_four_summary_cells_as_an_even_two_column_mobile_grid() -> None:
    mobile_css = product_harmony_css()
    assert ".portal-workspace-command-center .portal-dashboard-overview-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in mobile_css
    assert "@media (max-width: 460px)" not in dashboard_stat_rule(mobile_css)
```

- [ ] **Step 2: Run the dashboard test to verify it fails**

Run:

```powershell
& $py -m pytest -q tests/test_dashboard_workspace_command_center_contracts.py tests/test_product_harmony_ui_contracts.py -p no:cacheprovider
```

Expected: FAIL because the previous `460px` override collapses the four summary
cells into a visually uneven single column.

- [ ] **Step 3: Implement the final dashboard override**

Keep the existing four desktop cells and two-column tablet/mobile layout. In
the final theme layer, remove only the small-screen single-column override
for `.portal-dashboard-overview-stats`; let two equal columns remain down to
375px. Keep actions full width, cards auto-height, textual guarded states,
and the existing no-fake-count logic.

- [ ] **Step 4: Run the focused dashboard checks**

Run:

```powershell
& $py -m pytest -q tests/test_dashboard_workspace_command_center_contracts.py tests/test_product_harmony_ui_contracts.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit the dashboard slice**

```powershell
git add static/portal/portal-theme.css tests/test_dashboard_workspace_command_center_contracts.py tests/test_product_harmony_ui_contracts.py
git commit -m "fix: balance workspace dashboard summaries"
```

### Task 4: Rebalance Admin ERP into the shared light teal–sky system

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_product_harmony_ui_contracts.py`
- Regression: `tests/test_admin_erp_navigation_portal_contracts.py`
- Regression: `tests/test_admin_domain_centers_contracts.py`

- [ ] **Step 1: Add reviewed three-locale Admin overview chrome**

Add these fixed keys for `vi`, `en` and `zh` to the existing local catalogue:

```text
adminHome.title
adminHome.guard.kicker
adminHome.guard.verifiedTitle
adminHome.guard.pendingTitle
adminHome.metrics.users
adminHome.metrics.engineJobs
adminHome.metrics.workerJobs
adminHome.metrics.payments
adminHome.metrics.readiness
adminHome.queues.kicker
adminHome.queues.title
adminHome.queues.body
adminHome.readiness.kicker
adminHome.readiness.title
adminHome.readiness.body
adminHome.authority.summary
```

Keep API records, module titles delivered by the server, names, IDs and
canonical status values outside the translation catalogue.

- [ ] **Step 2: Replace only fixed Admin overview markup**

In `renderAdminOverview`, create a local `adminText` wrapper around `uiText`
and use it for the fixed labels above. Replace the literal `⌘` state icon with
`portalIcon(ICONS.security)`. Preserve `hasLiveCanonicalAdmin`, server-issued
route filtering, `refresh-admin` capability gating, `badge(...)` statuses and
the existing readiness row projection.

- [ ] **Step 3: Override dark legacy ERP paint in the final theme layer**

Use final, scoped token-only rules for:

```css
.portal-admin-home > .portal-admin-grid .portal-metric,
.portal-admin-work-queues,
.portal-admin-work-queue,
.portal-admin-authority,
.portal-admin-directory-group,
.portal-admin-directory-group > .portal-module-grid .portal-module-card
```

Map backgrounds to `--portal-surface-light` or
`--portal-surface-strong`, borders to `--portal-border`, body to
`--portal-muted`, heading text to `--portal-ink`, active/hover context to
`--portal-surface-soft` and focus to `--portal-context`. The final layer must
contain neither a raw colour nor `linear-gradient`.

- [ ] **Step 4: Run Admin/i18n contracts**

Run:

```powershell
& $py -m pytest -q tests/test_product_harmony_ui_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_admin_domain_centers_contracts.py -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit the Admin slice**

```powershell
git add static/portal/portal.js static/portal/portal-i18n.js static/portal/portal-theme.css tests/test_product_harmony_ui_contracts.py
git commit -m "feat: unify admin erp teal sky experience"
```

### Task 5: Run targeted visual QA, then prepare the PR

**Files:**
- Modify only if needed: `static/portal/portal-theme.css`
- Test: `tests/test_product_harmony_ui_contracts.py`
- Test: `tests/test_welcome_public_companion_contracts.py`
- Test: `tests/test_auth_entrypoint_layout_contracts.py`
- Test: `tests/test_dashboard_workspace_command_center_contracts.py`

- [ ] **Step 1: Start the app with a temporary local secret and disabled provider/payment flags**

```powershell
$env:WEB_SESSION_SECRET = 'local-product-harmony-only-secret'
$env:WEBAPP_PROVIDER_CALLS_ENABLED = '0'
$env:WEBAPP_PAYMENT_ENABLED = '0'
$env:WEBAPP_SESSION_DB_PATH = "$env:TEMP\toanaas-product-harmony-smoke.db"
& $py -m uvicorn app:app --host 127.0.0.1 --port 8766
```

Use only a fake local account. Do not use production credentials, submit a
payment, invoke Telegram, call a provider or create production data.

- [ ] **Step 2: Inspect real routes at desktop and mobile widths**

Use Browser/IAB to inspect `/welcome`, `/login`, signed `/dashboard`, and a
guarded `/admin` state at 1440px and 375px. Check five concrete points:

1. public and signed surfaces share tokens but do not share information density;
2. title/card/action/table edges align to the same rail;
3. primary text, secondary text and focus rings remain readable;
4. mobile dashboard remains two balanced summary columns and clears the dock;
5. Admin remains role-gated and does not display fake canonical values.

- [ ] **Step 3: Run critical regression commands**

```powershell
& $py -m pytest -q tests/test_product_harmony_ui_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_app_first_ui_system_contracts.py tests/test_dashboard_workspace_command_center_contracts.py tests/test_welcome_public_companion_contracts.py tests/test_auth_entrypoint_layout_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_admin_domain_centers_contracts.py -p no:cacheprovider
& $py -m compileall -q app.py
git diff --check
```

- [ ] **Step 4: Write a visual fidelity ledger and commit any final scoped correction**

Record concept evidence, desktop/mobile render evidence, correction and
remaining intentional deviation in
`docs/superpowers/specs/2026-07-27-product-harmony-teal-sky-design.md`.
Do not change backend authority or ship a screenshot as product UI.

- [ ] **Step 5: Commit and open the Web App PR**

```powershell
git add docs/superpowers/specs/2026-07-27-product-harmony-teal-sky-design.md static/portal/portal-theme.css tests/test_product_harmony_ui_contracts.py
git commit -m "docs: verify product harmony visual fidelity"
git push -u origin feature/p0-webapp-product-harmony
gh pr create --base main --title "Unify teal sky Web App product experience"
```

### Task 6: Landing-only follow-up after the Web App PR merges

**Repository:** `manhtoangreensky-wq/bot` (landing source only)

- [ ] Create a clean landing worktree/branch based on its current `main`.
- [ ] Use the shared design document’s public-companion rules to modify only
  `index.html` and its landing contracts.
- [ ] Keep Bot runtime, `bot.py`, PayOS, wallet, providers, webhook and lead
  request contract untouched.
- [ ] Open, CI-check and merge a Landing-only PR independently of the Web App
  PR.
