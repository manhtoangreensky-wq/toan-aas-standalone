# Admin Automation Monitor Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the existing signed `/admin/automation` receipt monitor a compact, readable light teal/cyan ERP surface without changing scheduler policy, receipts, read-only permissions, refresh/paging behavior, or any automation execution.

**Architecture:** Keep `portal.js`, `integration.js`, the monitor API, scheduler and server authorization untouched. Append one visual CSS layer rooted only at `.portal-page.portal-admin-automation-monitor` and add a static contract that proves scope, responsive behavior, semantic status visibility and reduced-motion safety. The UI must continue to say that monitoring is not a control plane and must never turn a redacted receipt into an auto-fix claim.

**Tech Stack:** FastAPI Portal shell, vanilla CSS (`static/portal/portal-theme.css`), existing JavaScript renderer, Python `pytest` static/authority contracts.

---

## File structure

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — one visual-only contract for Automation Monitor.
- Modify: `static/portal/portal-theme.css` — a single final route-scoped style layer.
- Create: `docs/superpowers/plans/2026-08-01-admin-automation-monitor-light-surface.md` — this record.

## Design constraints

- Use the accepted light high-trust teal/cyan ERP canvas; navigation remains shell-owned, and no marketing cards or fabricated KPIs appear.
- Preserve the monitor's real receipt hierarchy: current scheduler evidence, aggregate counters, redacted history and explicit non-control boundary.
- `read_only`/`processing` are context/info, `guarded` is warning and `failed` is danger. Text labels remain the source of meaning.
- Compact list rows align left metadata and right state without changing ordering, pagination or stale-read handling.
- At mobile sizes metrics become one column and existing controls stay 44px. No raw color, gradients, `transparent`, non-portal variables or CSS leakage beyond the route root.

### Task 1: Write a failing route-scoped visual contract

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_automation_monitor_final_surface_keeps_receipts_truthful`

- [x] **Step 1: Add the red test**

Append a test after the Operations Desk test. Extract `renderAdminAutomationMonitor`, assert the renderer includes `<article class="portal-page portal-admin-automation-monitor">`, then extract exactly this future CSS layer:

```python
layer = re.search(
    r"/\* Final light Admin Automation Monitor surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-admin-automation-monitor"
```

Require root, intro, metric, card, run row, boundary card, quiet/disabled controls, focus ring and badges. Require desktop two-column `.portal-operations-admin-grid`, 980px one-column grid, 700px one-column metrics and 44px controls, plus reduced-motion rules. Use the existing CSS-parser helpers; ensure every parsed selector begins with `root_scope`, allowed at-rules are exactly empty/980/700/reduced, and declarations contain no raw color/gradient/transparent/non-portal variable.

- [x] **Step 2: Prove red**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_automation_monitor_final_surface_keeps_receipts_truthful
```

Expected: it fails only because the final CSS marker does not exist.

### Task 2: Add the smallest honest monitor surface

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_automation_monitor_final_surface_keeps_receipts_truthful`

- [x] **Step 1: Append the token-only layer**

Append a layer after Operations Desk with this marker and root:

```css
/* Final light Admin Automation Monitor surface */
.portal-page.portal-admin-automation-monitor {
  color: var(--portal-ink);
  background: var(--portal-surface-light);
}

.portal-page.portal-admin-automation-monitor .portal-operations-admin-intro,
.portal-page.portal-admin-automation-monitor .portal-operations-boundary {
  border-color: var(--portal-border);
  background: var(--portal-surface-soft);
  box-shadow: none;
}

.portal-page.portal-admin-automation-monitor :is(button, a, input, select, textarea):focus-visible {
  outline: 3px solid var(--portal-focus) !important;
  outline-offset: 2px;
}
```

Style the existing metrics, cards and `portal-operations-run` rows with only portal tokens; source text is ink and supporting text is muted. Keep quiet controls stationary on hover. Use semantic badge tokens for `read_only`, `processing`, `guarded` and `failed`; keep all content truthful and server-owned.

- [x] **Step 2: Add responsive/reduced-motion safety**

At 980px make only the route's `.portal-operations-admin-grid` one column. At 700px make the metrics one column and retain 44px primary/quiet controls. At reduced motion, disable transition/transform for cards, metrics, run rows and buttons; do not affect other routes.

- [x] **Step 3: Prove green**

Run the focused test from Task 1. Expected: `1 passed`.

### Task 3: Verify no automation authority changed

**Files:**

- Test: `tests/test_admin_automation_monitor.py`
- Test: `tests/test_admin_automation_monitor_portal_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`

- [x] **Step 1: Run focused regression**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_admin_automation_monitor.py tests/test_admin_automation_monitor_portal_contracts.py tests/test_admin_erp_navigation.py
```

Expected: all tests pass. The monitor remains signed, redacted and read-only; browser refresh/paging cannot tick a scheduler, call Bot/provider/PayOS/wallet, deploy or mutate a job.

- [x] **Step 2: Verify scope**

```powershell
git diff --check
git diff -- static/portal/portal.js static/portal/integration.js app.py copyfast_admin_automation_monitor.py copyfast_operations.py
```

Expected: clean whitespace and no behavior-file diff.

- [x] **Step 3: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-automation-monitor-light-surface.md
git commit -m "Polish Admin Automation Monitor light surface"
```

## Self-review

- The CSS cannot leak to Operations Desk, Reliability, customer routes or other Admin screens because every selector is rooted at the monitor route.
- The change introduces no new scheduler data, count, control, refresh action, polling loop or approval claim.
- The evidence suite preserves server-side authorization, privacy/redaction, stale-result clearing and read-only actions while exercising the surface's highest-risk responsive/status paths.
