# Admin Audit Explorer Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the signed, redacted `/admin/audit` Explorer a dense, calm light teal/cyan ERP surface without changing its endpoint, filters, pagination, session checks, redaction or write boundaries.

**Architecture:** Add a route-only root class from the existing `renderAdmin` renderer when the already-normalized module is `audit`; this class has no data, authority or action effect. Add one final CSS layer rooted exclusively at that class and a static contract which prevents unscoped selectors, cascade regressions, raw colors and accidental backend/integration changes.

**Tech Stack:** FastAPI Portal shell, vanilla JavaScript renderer, vanilla CSS, Python static and authority contract tests.

---

## File structure

- Modify: `static/portal/portal.js` — attach a presentation-only `portal-admin-audit` class when `module === "audit"`.
- Modify: `static/portal/portal-theme.css` — final Audit Explorer light surface only.
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — route-scoped static visual/cascade contract.
- Create: `docs/superpowers/plans/2026-08-01-admin-audit-light-surface.md` — this execution record.

## Design and authority constraints

- Keep `/admin/audit` an aggregate, redacted, Web-native evidence surface. Do not add identity, event detail, raw logs, Bot/Core Bridge fallback, runtime control, provider data or fake audit records.
- Do not change `copyfast_admin_audit.py`, `static/portal/integration.js`, `app.py`, filter keys, pagination data, action names, request payloads, session checks or rendered copy.
- Reuse the existing labeled native select, buttons and tab order. Keep keyboard focus visible, 44px mobile controls and reduced-motion behavior.
- Every new selector is rooted at `.portal-page.portal-admin-audit`; use portal tokens only. The surface remains dense and aligned like an Odoo-style audit list, rather than a landing page or a faux real-time security console.

### Task 1: Add a failing route and cascade contract

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_audit_final_surface_keeps_redacted_receipts_clear`

- [x] **Step 1: Write the failing test**

Extract `renderAdmin(page, context)` and require this presentation-only branch:

```python
assert 'const pageClass = module === "audit" ? " portal-admin-audit" : "";' in renderer_source
assert '<article class="portal-page${pageClass}">' in renderer_source
```

Isolate the CSS layer with:

```python
layer = re.search(
    r"/\* Final light Admin Audit Explorer surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-admin-audit"
```

Use `_parse_css_rules` and `_css_declarations_for` to require tokenized root, guard, cards, audit metrics, labeled filter controls, data-table cells, pagination, boundaries, quiet/disabled controls, focus ring and `read_only`/`guarded`/`failed` badges. Require a base-rule order where the generic audit card comes before the audit boundary, so the soft boundary surface cannot be overridden. Reject selector leakage with `re.compile(rf"{re.escape(root_scope)}(?:$|(?=[\s>+~:#.\[]))")`, raw colors, RGB/HSL, gradients, `transparent`, non-portal variables and custom variables. Require only base, 980px, 700px and reduced-motion rule groups.

- [x] **Step 2: Prove red**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_audit_final_surface_keeps_redacted_receipts_clear
```

Expected: `FAIL` because the route class and `Final light Admin Audit Explorer surface` layer are absent.

### Task 2: Add the smallest presentation-only audit surface

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_audit_final_surface_keeps_redacted_receipts_clear`

- [x] **Step 1: Attach the route-only class**

Immediately after `const module = adminModuleKey(page, context);` in `renderAdmin`, add:

```javascript
const pageClass = module === "audit" ? " portal-admin-audit" : "";
```

Replace only the generic opening tag with:

```javascript
return `<article class="portal-page${pageClass}">${renderHero(page, context)}
```

Do not change any condition, action, data expression, text, request or closing markup.

- [x] **Step 2: Append route-scoped CSS**

Append `/* Final light Admin Audit Explorer surface */` after the prior final light layers. Root every selector at `.portal-page.portal-admin-audit`. Use portal tokens to set a light, dense, non-animated hierarchy for the guard, cards, audit metrics, `portal-project-filter`, select, data table, pagination and boundaries. Keep semantic badges visible; set a 3px focus outline; retain disabled controls as visibly disabled. Put the boundary rule after generic card rules so it keeps `var(--portal-surface-soft)`.

- [x] **Step 3: Add responsive and motion rules**

```css
@media (max-width: 980px) {
  .portal-page.portal-admin-audit .portal-work-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 700px) {
  .portal-page.portal-admin-audit :is(.portal-admin-grid, .portal-project-filter .portal-fields) {
    grid-template-columns: 1fr;
  }

  .portal-page.portal-admin-audit :is(.portal-button--primary, .portal-button--quiet, .portal-select) {
    min-height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .portal-page.portal-admin-audit :is(.portal-card, .portal-metric, .portal-project-filter, .portal-data-table tbody tr, .portal-button) {
    transition: none;
    transform: none;
  }
}
```

- [x] **Step 4: Prove green**

Run the Task 1 command again. Expected: `1 passed`.

### Task 3: Preserve Audit Explorer authority and hand off

**Files:**

- Test: `tests/test_copyfast_admin_audit.py`
- Test: `tests/test_admin_audit_portal_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`

- [x] **Step 1: Run focused regression**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_copyfast_admin_audit.py tests/test_admin_audit_portal_contracts.py tests/test_admin_erp_navigation.py
```

Expected: all pass; no raw identity/detail, browser authority, endpoint change or unsafe audit mutation appears.

- [x] **Step 2: Verify diff boundary**

```powershell
git diff --check
git diff -- copyfast_admin_audit.py static/portal/integration.js app.py copyfast_auth.py
```

Expected: clean; the behavior files named above have no diff.

- [x] **Step 3: Commit**

```powershell
git add static/portal/portal.js static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-audit-light-surface.md
git commit -m "Polish Admin Audit Explorer light surface"
```

## Self-review

- The only JavaScript change is a route-specific class computed from the existing `module`; it cannot change the Audit API, data projection, permissions, filter/page action or controls.
- Audit facts remain redacted and read-only; CSS does not imply remediation, live monitoring or a security claim.
- The static contract covers route scope, CSS cascade ordering, semantic statuses, keyboard focus, mobile density and reduced motion.
