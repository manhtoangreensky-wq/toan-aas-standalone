# TOAN AAS Teal–Sky Rebalance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance App access, Workspace and ERP into one professional teal–sky interface without changing security or product authority.

**Architecture:** Keep FastAPI routes, server-rendered shell and vanilla-JS rendering intact. `portal-theme.css` becomes the final semantic visual authority. Obsolete access-only declarations in `portal.css` are removed or neutralized, so a late legacy rule cannot reintroduce dark backgrounds or a two-column split.

**Tech Stack:** FastAPI, HTML, CSS, vanilla JavaScript, pytest static contracts.

---

### Task 1: Lock the visual and access regressions with contracts

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `tests/test_login_app_ux_contracts.py`
- Modify: `tests/test_dashboard_workspace_command_center_contracts.py`

- [ ] **Step 1: Write failing token tests**

```python
def test_rebalanced_teal_sky_tokens_keep_private_main_light_and_rail_deep() -> None:
    for declaration in (
        "--portal-app-canvas: #f4fbfc;",
        "--portal-surface-light: #ffffff;",
        "--portal-action: #0f766e;",
        "--portal-context: #0284c7;",
        "--portal-rail: #083344;",
    ):
        assert declaration in THEME
```

- [ ] **Step 2: Write failing access geometry tests**

```python
def test_access_flow_has_one_balanced_column_without_legacy_split_pressure() -> None:
    assert "grid-template-columns: minmax(0, min(100%, 480px));" in ACCESS_THEME
    assert 'grid-template-areas: "header" "intro" "card";' in ACCESS_THEME
    assert "border-right: 0;" in ACCESS_THEME
    assert "max-width: 11ch;" not in ACCESS_THEME
```

- [ ] **Step 3: Run and verify the intended initial failure**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q --noconftest tests/test_teal_cyan_ui_foundation_contracts.py tests/test_login_app_ux_contracts.py tests/test_dashboard_workspace_command_center_contracts.py
```

Expected: only the new token/geometry assertions fail.

- [ ] **Step 4: Commit the red contracts**

```powershell
git add tests/test_teal_cyan_ui_foundation_contracts.py tests/test_login_app_ux_contracts.py tests/test_dashboard_workspace_command_center_contracts.py
git commit -m "test: lock teal sky rebalance contracts"
```

### Task 2: Make the theme layer the only visual authority

**Files:**
- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal.css`
- Modify: `design-system/toan-aas-web-app/MASTER.md`

- [ ] **Step 1: Define semantic tokens in the final theme**

```css
:root {
  --portal-app-canvas: #f4fbfc;
  --portal-surface-light: #ffffff;
  --portal-ink: #083344;
  --portal-action: #0f766e;
  --portal-brand: #14b8a6;
  --portal-context: #0284c7;
  --portal-rail: #083344;
  --portal-light-border: #d7ecef;
  --portal-light-muted: #486b75;
}
```

- [ ] **Step 2: Map signed surfaces to the roles**

```css
.portal-shell:not(.portal-shell--auth):not(.portal-shell--landing),
.portal-workspace,
.portal-main { background: var(--portal-app-canvas); color: var(--portal-ink); }

.portal-sidebar { background: var(--portal-rail); }
.portal-header,
.portal-card,
.portal-data-table-wrap { background: var(--portal-surface-light); }
```

Do not restyle actual job/payment status data or change a route/action binding.

- [ ] **Step 3: Delete only obsolete late access declarations**

Remove the late dark `.portal-body--auth` / `.portal-shell--auth` block and
the `.portal-auth-page--access` two-column grid block from `portal.css`.
Do not append `!important` to hide a conflict. Preserve generic auth
semantics used by non-access routes.

- [ ] **Step 4: Update the master design system and verify**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q --noconftest tests/test_teal_cyan_ui_foundation_contracts.py tests/test_dashboard_workspace_command_center_contracts.py
git add static/portal/portal-theme.css static/portal/portal.css design-system/toan-aas-web-app/MASTER.md tests/test_teal_cyan_ui_foundation_contracts.py tests/test_dashboard_workspace_command_center_contracts.py
git commit -m "feat: rebalance teal sky workspace surfaces"
```

### Task 3: Replace the access split with a centred progressive form

**Files:**
- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal-i18n.js` only if fixed visible copy changes
- Modify: `tests/test_login_app_ux_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Implement the centered route frame**

```css
.portal-auth-page--access {
  grid-template-columns: minmax(0, min(100%, 480px));
  grid-template-areas: "header" "intro" "card";
  justify-content: center;
  width: min(100% - 32px, 560px);
  row-gap: 20px;
}
.portal-auth-page--access .portal-auth-intro {
  justify-items: center;
  padding: 8px 0 0;
  border-right: 0;
  text-align: center;
}
```

- [ ] **Step 2: Preserve server-owned actions**

Keep `data-portal-*` bindings, autocomplete, visible labels, password
visibility, recovery, CSRF, enabled-provider handling and optional Telegram
disclosure. Do not add local browser identity state or fake providers.

- [ ] **Step 3: Add reviewed locale keys only when copy changes**

```javascript
assertLocaleKeysetsEqual("access.title", "access.description");
```

Use existing locale helpers and never translate project/provider values.

- [ ] **Step 4: Verify and commit**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q --noconftest tests/test_login_app_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
git add static/portal/portal-theme.css static/portal/portal-i18n.js tests/test_login_app_ux_contracts.py
git commit -m "feat: centre the secure workspace access flow"
```

### Task 4: Validate the accessible responsive result

**Files:**
- Modify: `docs/superpowers/specs/2026-07-27-teal-sky-rebalance-design.md`

- [ ] **Step 1: Start only the local app with writes disabled**

```powershell
$env:WEBAPP_PROVIDER_CALLS_ENABLED='false'
$env:WEBAPP_PAYMENT_ENABLED='false'
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: Verify the real anonymous routes**

At 375px, 768px, 1024px and desktop inspect `/login`, `/register`,
`/welcome` and a safe signed shell. Check no horizontal scroll, 44px mobile
controls, focus visibility, reduced motion and natural Vietnamese line breaks.
Do not submit credentials or invoke a provider.

- [ ] **Step 3: Run final targeted validation and commit**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q --noconftest tests/test_teal_cyan_ui_foundation_contracts.py tests/test_login_app_ux_contracts.py tests/test_dashboard_workspace_command_center_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
git diff --check
```

Record the visual comparison in the design spec and request a review before
opening the App-only PR.
