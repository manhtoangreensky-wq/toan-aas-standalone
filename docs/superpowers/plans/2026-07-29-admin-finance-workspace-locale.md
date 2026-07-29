# Admin Finance Workspace Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present the existing signed Admin Finance hub and Tax Readiness guide
in the reviewed VI/EN/ZH interface locale without changing financial authority
or data behavior.

**Architecture:** Fixed UI strings live in a new equal-key Portal i18n
catalogue. A narrow Portal helper consumes that catalogue for the Finance
domain and Tax Readiness renderer, while server-issued data stays escaped
runtime data. No server, bridge or data-model code changes.

**Tech Stack:** Browser JavaScript, existing `TOANAASI18n` catalogue, Python
static contract tests, Node syntax check.

---

### Task 1: Lock the locale and safety contract

**Files:**
- Create: `tests/test_admin_finance_workspace_locale_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Write a failing focused contract test**

```python
def test_admin_finance_workspace_fixed_copy_uses_reviewed_locale_catalogue() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    assert "const ADMIN_FINANCE_WORKSPACE_MESSAGES" in i18n
    assert "function adminFinanceText(key, fallback, params)" in portal
    assert "function adminFinanceDomain" in portal
    assert "function renderAdminTaxReadiness" in portal
    for locale in ("vi", "en", "zh"):
        assert f"{locale}: {{" in i18n
    for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage"):
        assert forbidden not in _function_source(portal, "renderAdminTaxReadiness")
```

- [ ] **Step 2: Run the test and confirm the helper/catalogue assertions fail**

Run: `python -m pytest -q tests/test_admin_finance_workspace_locale_contracts.py`

Expected: fail because the new catalogue and helper do not exist.

- [ ] **Step 3: Extend the existing i18n runtime key list**

Add representative `adminFinance.*` keys to the Node-backed list in
`tests/test_portal_i18n_bundle_contracts.py`, including Finance stream,
Tax Readiness checklist and explicit no-ledger boundary strings.

- [ ] **Step 4: Commit the red contract**

```powershell
git add tests/test_admin_finance_workspace_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py
git commit -m "Test Admin Finance workspace locale contract"
```

### Task 2: Add fixed Finance Workspace translations

**Files:**
- Modify: `static/portal/portal-i18n.js: after FINANCE_PLANNING_MESSAGES`
- Modify: `static/portal/portal.js: renderAdminDomain and renderAdminTaxReadiness`

- [ ] **Step 1: Add the equal-key catalogue**

Define `ADMIN_FINANCE_WORKSPACE_MESSAGES` with `adminFinance.*` keys in each
of `vi`, `en` and `zh`, then merge it alongside
`FINANCE_PLANNING_MESSAGES`. Include only static chrome: Finance center
copy, seven stream labels/descriptions, route/empty/authority messages,
Tax Readiness checklist, safe handoff and boundaries.

- [ ] **Step 2: Add the narrow locale helpers and Finance projection**

```javascript
function adminFinanceText(key, fallback, params) {
  return uiText(`adminFinance.${key}`, fallback, params);
}

function adminFinanceDomain() {
  return {
    kicker: adminFinanceText("hub.kicker", "Finance & revenue control center"),
    title: adminFinanceText("hub.title", "Financial operations with one ledger authority"),
    description: adminFinanceText("hub.description", "Open reviewed finance workflows without creating a second ledger."),
    streams: [/* existing fixed routes/icons with localized title/text */],
    boundaries: [/* localized fixed boundary text */]
  };
}
```

Use this projection only when the normalized page path is `/admin/finance`.
Use `adminFinanceText` for all fixed Tax Readiness strings. Retain
`safeText(data.message)`, `safeText(stream.title)`, route authorization,
`renderNotes(page)`, existing icons, badges, and all route/data behavior.

- [ ] **Step 3: Run the focused contracts and JavaScript syntax checks**

Run:

```powershell
python -m pytest -q tests/test_admin_finance_workspace_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_finance_planning_portal_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
git diff --check
```

Expected: all focused tests and both syntax checks pass; no whitespace errors.

- [ ] **Step 4: Commit the implementation**

```powershell
git add static/portal/portal-i18n.js static/portal/portal.js tests/test_admin_finance_workspace_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py
git commit -m "Localize Admin Finance workspace"
```

### Task 3: Review and publish the isolated Web-only change

**Files:**
- Verify: `docs/superpowers/specs/2026-07-29-admin-finance-workspace-locale-design.md`
- Verify: `docs/superpowers/plans/2026-07-29-admin-finance-workspace-locale.md`

- [ ] **Step 1: Review scope**

Confirm the diff does not include backend routes, Bot code, bridge, payment,
wallet, provider, finance planning storage, server data models or unrelated
Portal surfaces.

- [ ] **Step 2: Re-run the focused gate and inspect the diff**

Run the Task 2 commands and `git status --short`. Confirm only the locale
catalogue, Portal renderer, focused tests and task documentation change.

- [ ] **Step 3: Push and open a PR only after the focused gate is green**

```powershell
git push -u origin feature/p0-webapp-copyfast167-admin-finance-workspace-locale
gh pr create --repo manhtoangreensky-wq/toan-aas-standalone --base main --head feature/p0-webapp-copyfast167-admin-finance-workspace-locale --title "Localize Admin Finance workspace"
```
