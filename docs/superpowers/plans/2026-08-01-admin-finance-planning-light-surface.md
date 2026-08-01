# Finance Operations Planning Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing signed Admin Finance Operations Planning workbench as calm, dense, responsive and legible as the completed teal/cyan customer and Admin surfaces without changing any planning, payment, Bot or ledger behavior.

**Architecture:** Keep the route renderer, finance-planning API, confirmation flow and server authority untouched. Add one final CSS layer scoped only to `.portal-page.portal-finance-planning`, with a static contract that proves token-only styling, semantic status visibility, focus treatment, responsive collapse and reduced-motion safety.

**Tech Stack:** FastAPI portal shell, vanilla `static/portal/portal.js`, tokenized CSS in `static/portal/portal-theme.css`, Python `pytest` static-contract suite.

---

## File structure

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — add one red/green static contract for the final Finance Planning layer; it owns only visual-scope assertions.
- Modify: `static/portal/portal-theme.css` — append the Finance Planning layer after the existing final-light layers; it owns presentation only.
- Create: `docs/superpowers/plans/2026-08-01-admin-finance-planning-light-surface.md` — this implementation record.

### Task 1: Lock the visual contract before styling

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_finance_operations_planning_final_surface_keeps_internal_planning_clear`

- [x] **Step 1: Write the failing test**

Add a test after `test_light_delivery_center_final_surface_keeps_canonical_states_clear` that extracts exactly this CSS layer:

```python
layer = re.search(
    r"/\* Final light Finance Operations Planning surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-finance-planning"
```

The test must require token-only rules for the route root, the planning intro, metrics, summary/list tables, forms, read-state, lifecycle/status badges, quiet actions and focus ring. It must also require a `980px` one-column authoring collapse, `700px` 44px controls plus one-column metrics/tables, and reduced motion rules. It must reject raw colors, gradients, non-portal variables and selectors outside `root_scope`.

- [x] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_finance_operations_planning_final_surface_keeps_internal_planning_clear
```

Expected: failure because `Final light Finance Operations Planning surface` does not exist yet.

### Task 2: Implement the smallest scoped light surface

**Files:**
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_finance_operations_planning_final_surface_keeps_internal_planning_clear`

- [x] **Step 1: Append the CSS layer**

Append a marker and selectors whose every selector begins with `.portal-page.portal-finance-planning`. Preserve the dense ERP layout and the existing lifecycle wording; do not add or alter HTML, actions, API calls, localization or `portal.js`.

```css
/* Final light Finance Operations Planning surface */
.portal-page.portal-finance-planning {
  color: var(--portal-ink);
}

.portal-page.portal-finance-planning .portal-operations-metrics .portal-metric,
.portal-page.portal-finance-planning .portal-card,
.portal-page.portal-finance-planning .portal-operations-admin-intro {
  border-color: var(--portal-border);
  background: var(--portal-surface-light);
  box-shadow: none;
}

.portal-page.portal-finance-planning :is(.portal-data-table th, .portal-form-note) {
  color: var(--portal-muted);
}

.portal-page.portal-finance-planning :is(.portal-data-table td, .portal-card-title, h2, strong) {
  color: var(--portal-ink);
}

.portal-page.portal-finance-planning :is(button, a, input, select, textarea):focus-visible {
  outline: 3px solid var(--portal-focus) !important;
  outline-offset: 2px;
}
```

Use the established token-only pattern for semantic status colors: `ready`/active remains success, `processing`/review remains info, `guarded` remains warning, and failed stays danger. Use stationary hover treatment (`transform: none`, `box-shadow: none`) and preserve all disabled control states.

- [x] **Step 2: Add responsive and reduced-motion rules**

At `max-width: 980px`, make only `.portal-work-grid` one column. At `max-width: 700px`, collapse `.portal-operations-metrics` to one column, keep all primary/quiet controls at `min-height: 44px`, avoid a horizontal page overflow, and make finance tables readable through their existing table-scroll model rather than changing their data. At `prefers-reduced-motion: reduce`, set the layer’s card/button/table-row transitions to `none` and transforms to `none`.

- [x] **Step 3: Run the focused test to verify it passes**

Run the exact command from Task 1. Expected: `1 passed`.

### Task 3: Prove that the visual layer did not affect finance authority

**Files:**
- Test: `tests/test_finance_planning_portal_contracts.py`
- Test: `tests/test_copyfast_finance_planning.py`
- Test: `tests/test_admin_finance_workspace_locale_contracts.py`

- [x] **Step 1: Run focused regression tests**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_finance_planning_portal_contracts.py tests/test_copyfast_finance_planning.py tests/test_admin_finance_workspace_locale_contracts.py
```

Expected: all selected tests pass; no newly introduced import, provider, payment, Bot or bridge behavior exists.

- [x] **Step 2: Check the patch boundary**

Run:

```powershell
git diff --check
git diff -- static/portal/portal.js copyfast_finance_planning.py copyfast_api.py app.py
```

Expected: whitespace check is clean and the second diff is empty.

- [ ] **Step 3: Commit the focused UI slice**

Run:

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-finance-planning-light-surface.md
git commit -m "Polish finance planning light surface"
```

Expected: one focused commit containing only the CSS layer, its static contract and this plan.

## Self-review

- Scope is limited to the existing Web-local Finance Planning route; it neither touches a Bot authority nor introduces a payment, top-up, refund, provider, bridge, job or ledger path.
- The static contract covers the state semantics and responsive/reduced-motion behavior most likely to regress in a dense internal workbench.
- The only new selectors begin with the Finance Planning route root, so this visual layer cannot leak into customer or other Admin pages.
