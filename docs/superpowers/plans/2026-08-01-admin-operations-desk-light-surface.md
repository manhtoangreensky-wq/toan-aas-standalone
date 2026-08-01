# Operations Desk Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing signed `/admin/work-queue` Operations Desk a dense, calm and readable light teal/cyan ERP work surface without changing its server-authorized read-only queue, filters, routes, or actions.

**Architecture:** Leave `portal.js`, `integration.js`, Operations Desk APIs and the signed-role boundary untouched. Append one token-only CSS layer, strictly rooted at `.portal-page.portal-operations-desk`, and protect it with a static visual contract. The workbench keeps its real source availability, guarded state and fixed server filters; no new KPI, route, queue item, action or automatic remediation is invented.

**Tech Stack:** FastAPI Portal shell, vanilla CSS in `static/portal/portal-theme.css`, existing JavaScript renderer, Python `pytest` static-contract suites.

---

## File structure

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — visual-scope contract only; it must not re-test or change Operations Desk authority.
- Modify: `static/portal/portal-theme.css` — one final, route-scoped Operations Desk presentation layer.
- Create: `docs/superpowers/plans/2026-08-01-admin-operations-desk-light-surface.md` — this execution record.

## Design constraints

- Maintain the accepted high-trust, light teal/cyan ERP system: dark rail is shell-owned; workbench surfaces stay light, compact and aligned.
- Keep the existing queue table and its table-scroll model. Do not convert server-backed rows into invented cards, and do not replace `—` or `guarded` with a zero/healthy claim.
- Source metrics, filter labels and primary task titles align to one grid. Filters collapse before the table is forced to overflow the page.
- `read_only` remains contextual/info, `guarded` remains warning, `completed` remains success and `failed` remains danger; each existing badge still includes its text label.
- Preserve keyboard focus, 44px mobile controls and reduced-motion behavior. No raw colors, gradients, `transparent`, non-portal variables or behavior selectors are permitted in this layer.

### Task 1: Lock the route-scoped visual contract before styling

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_operations_desk_final_surface_keeps_erp_queue_aligned_and_truthful`

- [x] **Step 1: Write the failing test**

Add a test after the Finance Planning surface test. It must verify the existing renderer continues to use the exact root class and then extract only the proposed final layer:

```python
start = portal_source.index("  function renderOperationsDesk(")
next_renderer = portal_source.find("\n  function ", start + 1)
renderer_source = portal_source[start : next_renderer if next_renderer >= 0 else None]
assert '<article class="portal-page portal-operations-desk">' in renderer_source

layer = re.search(
    r"/\* Final light ERP Operations Desk surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
```

The contract must require tokenized styles for the route root, ERP intro, source metrics, cards, filter fields, queue table, quiet controls, focus ring and the four existing semantic badge classes. It must require the 980px filter collapse, 700px one-column metrics/filter plus 44px control target, and a reduced-motion rule. Parse every selector and reject selectors outside `.portal-page.portal-operations-desk`, raw colors, gradients, `transparent`, or custom properties outside the `--portal-*` family.

- [x] **Step 2: Run the focused test to verify it fails for the expected reason**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_operations_desk_final_surface_keeps_erp_queue_aligned_and_truthful
```

Expected: failure because `Final light ERP Operations Desk surface` does not exist.

### Task 2: Add the smallest truthful Operations Desk surface

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_operations_desk_final_surface_keeps_erp_queue_aligned_and_truthful`

- [x] **Step 1: Append the scoped CSS layer**

Append this marker after the Finance Planning layer. Every ordinary selector starts with the Operations Desk root; add no HTML, JavaScript, request or action changes.

```css
/* Final light ERP Operations Desk surface */
.portal-page.portal-operations-desk {
  color: var(--portal-ink);
  background: var(--portal-surface-light);
}

.portal-page.portal-operations-desk .portal-operations-admin-intro,
.portal-page.portal-operations-desk .portal-card {
  border-color: var(--portal-border);
  background: var(--portal-surface-light);
  box-shadow: none;
}

.portal-page.portal-operations-desk .portal-operations-metrics .portal-metric {
  border-color: var(--portal-border);
  background: var(--portal-surface-light);
  box-shadow: none;
}

.portal-page.portal-operations-desk :is(button, a, input, select, textarea):focus-visible {
  outline: 3px solid var(--portal-focus) !important;
  outline-offset: 2px;
}
```

Continue the same layer for the existing `.portal-support-filter`, `.portal-field`, `.portal-select`, `.portal-data-table-wrap`, `.portal-data-table`, `.portal-button--quiet`, disabled controls and `.portal-badge[data-status]`. Use stationary hover treatment (`transform: none` and `box-shadow: none`). Let the existing table wrapper keep horizontal containment; do not change data order, make a new action or create a browser-owned state.

- [x] **Step 2: Add responsive and motion-safe rules**

At `max-width: 980px`, collapse only the Operations Desk filter fields to two equal columns and keep footer actions in their existing order. At `max-width: 700px`, use one source-metric and filter column, set existing primary/quiet buttons to `min-height: 44px`, and keep the table in its wrapper. At `prefers-reduced-motion: reduce`, turn off the layer's transitions and transforms for cards, metrics, filter controls, quiet controls and table rows.

- [x] **Step 3: Run the focused test to verify it passes**

Run the command from Task 1. Expected: `1 passed`.

### Task 3: Prove the CSS did not widen queue authority

**Files:**

- Test: `tests/test_operations_desk.py`
- Test: `tests/test_operations_desk_portal_contracts.py`
- Test: `tests/test_operations_desk_read_model_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`

- [x] **Step 1: Run the important regression suite**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_operations_desk.py tests/test_operations_desk_portal_contracts.py tests/test_operations_desk_read_model_contracts.py tests/test_admin_erp_navigation.py
```

Expected: all selected tests pass; the operation remains server-authorized, read-only, redacted and fixed-filtered.

- [x] **Step 2: Verify patch boundaries and production-readiness evidence**

Run:

```powershell
git diff --check
git diff -- static/portal/portal.js static/portal/integration.js app.py copyfast_operations_desk.py
```

Expected: the whitespace check is clean and the second diff is empty. After merge and deploy, make read-only requests to `https://app.toanaas.vn/health` and the deployed CSS; do not trigger staff actions, provider calls, payments, Bot access or queue mutations.

- [x] **Step 3: Commit the focused UI slice**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-operations-desk-light-surface.md
git commit -m "Polish Operations Desk light surface"
```

Expected: one focused commit containing only the CSS layer, its static contract and this plan.

## Self-review

- The target is one signed Admin ERP route with existing meaningful workflow; no generic landing-page treatment is introduced.
- The new layer cannot style customers, other Admin routes or runtime/product features because every selector is rooted at `.portal-page.portal-operations-desk`.
- The queue's server-owned filters, availability semantics, redacted projection, refresh/paging actions, role enforcement and API behavior remain outside this diff and are covered by focused regression tests.
