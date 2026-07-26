# TOAN AAS Unified Teal–Sky UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app-owned public entry, access flow and signed Workspace
feel like one professional Vietnamese-first teal–sky product without changing
product authority or fabricating data.

**Architecture:** Keep the FastAPI/vanilla-JS route and data model intact.
`portal-theme.css` is the final visual authority loaded after the legacy
catalogue; `portal.js` changes only fixed presentation markup/copy where a
layout boundary cannot be achieved in CSS.  Existing i18n remains the source
of reviewed `vi`/`en`/`zh` display text.

**Tech Stack:** FastAPI, server-rendered Portal shell, vanilla JavaScript,
semantic CSS tokens, Portal i18n, pytest/Node browser-bundle contracts.

---

### Task 1: Establish a single semantic teal–sky foundation

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `design-system/toan-aas-web-app/MASTER.md`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Write a failing token contract**

```python
def test_unified_teal_sky_tokens_drive_light_and_dark_surfaces() -> None:
    for token in (
        "--portal-bg: #062a36;",
        "--portal-surface: #0b3440;",
        "--portal-accent: #14b8a6;",
        "--portal-info: #38bdf8;",
        "--portal-light-canvas: #f4fbfc;",
    ):
        assert token in root_declarations
    assert "#14b8a6" not in rendered_rules
```

- [ ] **Step 2: Run the focused contract and verify it fails**

Run: `python -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py`

Expected: FAIL because the old token values are still the visual authority.

- [ ] **Step 3: Replace the final theme tokens and shared chrome rules**

```css
:root {
  --portal-bg: #062a36;
  --portal-surface: #0b3440;
  --portal-surface-strong: #104352;
  --portal-border: #246070;
  --portal-accent: #14b8a6;
  --portal-accent-hover: #2dd4bf;
  --portal-info: #38bdf8;
  --portal-light-canvas: #f4fbfc;
  --portal-light-border: #d7ecef;
  --portal-ink: #092b36;
}
```

Keep `portal-button`, `portal-input`, `portal-card`, sidebar, header, table,
focus and reduced-motion selectors token-driven.  Do not edit route/actions
or add public caching for private paths.

- [ ] **Step 4: Update the Master design-system override**

Record the exact palette, spacing scale, light/dark ownership, typography and
no-raw-hex invariant so later page work cannot drift back to purple/pink or
one-off colors.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py`

Expected: PASS.

```bash
git add static/portal/portal-theme.css design-system/toan-aas-web-app/MASTER.md tests/test_teal_cyan_ui_foundation_contracts.py
git commit -m "Unify teal sky visual tokens"
```

### Task 2: Rebuild the app-owned public landing hierarchy

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Test: `tests/test_welcome_public_companion_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Write a failing public-surface contract**

```python
def test_welcome_uses_one_public_container_and_real_workflow_preview() -> None:
    assert ".portal-landing-public-container" in THEME
    assert "landing.hero.title" in PORTAL
    assert "landing.preview.guardedBody" in PORTAL
    assert "fetch(" not in landing_renderer
```

- [ ] **Step 2: Run it and verify the expected failure**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py tests/test_portal_i18n_bundle_contracts.py`

Expected: FAIL before the public-container/token contract is added.

- [ ] **Step 3: Apply the landing layout without changing the public route**

Use the existing `renderLanding` section order and reviewed locale keys.  Add
one public container class only if CSS cannot target the existing structure.
Make navigation, hero, preview, Studio cards, workflow, trust, final CTA and
footer share aligned edges.  The preview describes `draft → estimate →
confirm → delivery`; it must not show an unverified live result, customer
record or fabricated job count.

- [ ] **Step 4: Review landing copy in all three locales**

Keep visible action wording concise: `Bắt đầu Workspace`, `Đăng nhập`,
`Khám phá Studio`.  Add matching `landing.*` keys in `vi`, `en`, `zh`; run
the Node keyset contract so no locale falls back to Vietnamese.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py`

Expected: PASS with no public data fetch, private cache or fake output.

```bash
git add static/portal/portal-theme.css static/portal/portal-i18n.js static/portal/portal.js tests/test_welcome_public_companion_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
git commit -m "Refresh public teal sky landing"
```

### Task 3: Make login and registration balanced, compact and safe

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Test: `tests/test_login_app_ux_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add failing layout/locale assertions**

```python
def test_access_flow_has_a_bounded_centered_form_without_word_by_word_heading_wrap() -> None:
    assert "max-width: 520px;" in ACCESS_THEME
    assert "text-wrap: balance;" in ACCESS_THEME
    assert "min-height: 44px;" in ACCESS_THEME
```

- [ ] **Step 2: Run the focused contract and verify it fails**

Run: `python -m pytest -q tests/test_login_app_ux_contracts.py`

Expected: FAIL until the final access layout overrides the legacy split rules.

- [ ] **Step 3: Implement the centred access flow**

Keep the real Email/password form, server-controlled OAuth availability,
Telegram linking disclosure, CSRF and password recovery routes.  Recompose
the existing intro/card in CSS into a bounded centred flow: short title,
visible labels, 44px controls, a compact login/register switch and progressive
OAuth/Telegram disclosure.  Do not add a remember-me control, social login
that the server has not enabled, local storage or a fake account state.

- [ ] **Step 4: Localize every new fixed access label**

Add exact `access.*` entries in all three locales and extend the Node runtime
key contract.  Keep Telegram identity language neutral: linking is optional
and does not promise canonical data until its verified state is ready.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest -q tests/test_login_app_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py`

Expected: PASS.

```bash
git add static/portal/portal-theme.css static/portal/portal-i18n.js static/portal/portal.js tests/test_login_app_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
git commit -m "Refine access experience"
```

### Task 4: Align the signed Workspace and mobile shell

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal.css`
- Modify: `static/portal/portal-i18n.js`
- Test: `tests/test_dashboard_workspace_command_center_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add a failing shared-shell contract**

```python
def test_signed_shell_keeps_operational_density_with_aligned_mobile_controls() -> None:
    assert ".portal-sidebar" in THEME
    assert ".portal-header" in THEME
    assert "grid-template-columns: minmax(0, 1fr);" in mobile_theme
    assert "min-height: 44px;" in mobile_theme
    assert "linear-gradient" not in workspace_theme
```

- [ ] **Step 2: Run the contract and verify it fails before layout updates**

Run: `python -m pytest -q tests/test_dashboard_workspace_command_center_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py`

Expected: FAIL for the new shared-shell geometry assertions.

- [ ] **Step 3: Implement aligned app shell primitives**

Keep the existing sidebar, header, Dashboard lanes, table wrappers and five
item mobile navigation.  Normalize spacing, headings, button groups, card
edges, table dividers, selected navigation and status rows.  The Dashboard
continues to show only real owner-scoped metadata, guarded states and explicit
empty states; do not introduce sample metrics/charts from the visual concept.

- [ ] **Step 4: Verify the responsive language boundary**

Check the `vi`, `en`, `zh` shell in Node at first mount.  Fixed labels must
come from `portal-i18n.js`; project names, IDs, amounts, dates and provider
status remain server/customer values.  Check 375px, 768px, 1024px and 1440px
for no horizontal overflow and no hidden content behind navigation.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest -q tests/test_dashboard_workspace_command_center_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py`

Expected: PASS.

```bash
git add static/portal/portal-theme.css static/portal/portal.css static/portal/portal-i18n.js tests/test_dashboard_workspace_command_center_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
git commit -m "Align teal sky workspace shell"
```

### Task 5: Visual and functional handoff

**Files:**

- Modify: `docs/superpowers/specs/2026-07-27-unified-teal-sky-ui-design.md`
- Test: focused suite from Tasks 1–4

- [ ] **Step 1: Start the local FastAPI app with provider/payment flags disabled**

```powershell
$env:WEBAPP_PROVIDER_CALLS_ENABLED = 'false'
$env:WEBAPP_PAYMENT_ENABLED = 'false'
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: Capture public, access and signed-shell screenshots**

Inspect `/welcome`, `/login`, `/register` and a signed/mock-safe `/dashboard`
at desktop and 390px mobile.  Compare them against the four concept paths in
the design spec.  Record five checks: palette, container alignment, type
scale, focus/touch states, and responsive navigation.

- [ ] **Step 3: Run the final critical verification**

```powershell
python -m pytest -q `
  tests/test_teal_cyan_ui_foundation_contracts.py `
  tests/test_welcome_public_companion_contracts.py `
  tests/test_login_app_ux_contracts.py `
  tests/test_dashboard_workspace_command_center_contracts.py `
  tests/test_portal_i18n_bundle_contracts.py `
  tests/test_portal_safety_contracts.py `
  tests/test_interface_locale_narrow_update_and_first_paint.py
python -m compileall -q .
git diff --check
```

- [ ] **Step 4: Commit the verification ledger and open one focused PR**

Document the screenshot comparison and remaining intentional deviations in
the design spec.  Only then commit the final documentation and create a PR;
do not deploy production providers or alter Railway environment variables.
<!-- End of plan. -->
