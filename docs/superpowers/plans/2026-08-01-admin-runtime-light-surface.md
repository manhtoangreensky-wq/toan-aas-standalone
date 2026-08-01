# Admin Runtime Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give signed `/admin/runtime` its own dense light teal/cyan operations surface while preserving the existing canonical job metadata, confirm/retry/refund guards and no-browser-infrastructure boundary.

**Architecture:** Extend the existing presentation-only `pageClass` calculation in `renderAdmin` to select `portal-admin-runtime` only for the existing normalized `runtime` module; route data, actions, permissions, requests and text remain untouched. Add one CSS layer rooted only at that class plus static contracts that preserve the prior Audit class and prevent unscoped or non-tokenized styling.

**Tech Stack:** FastAPI Portal shell, vanilla JavaScript renderer, vanilla CSS, Python static and authority contract tests.

---

## Baseline note

`origin/main` at `058037c` has one unrelated existing failure in `tests/test_system_data_stewardship_portal_contracts.py::test_audit_contract_is_finite_and_keeps_payment_video_and_bot_state_out_of_browser`: `scripts/migration/audit_bot_to_web.py` places `"menu|billing"` in the System/Data registry while that test expects it outside. This Runtime PR does not modify either file; focused Runtime authority tests are used for this bounded change.

## File structure

- Modify: `static/portal/portal.js` — extend only the route class mapping for `audit` and `runtime`.
- Modify: `static/portal/portal-theme.css` — final Runtime light surface only.
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — route-scoped visual/cascade contract and revised Audit class assertion.
- Create: `docs/superpowers/plans/2026-08-01-admin-runtime-light-surface.md` — this execution record.

## Design and authority constraints

- Runtime remains a canonical metadata and queue view. Do not add deploy, restart, worker control, provider calls, raw logs, live-monitoring claims, fake health values or infrastructure repair controls.
- Do not change `static/portal/integration.js`, `app.py`, `copyfast_auth.py`, bridge logic, job action names, confirmation flow, CSRF, idempotency, ownership, retry/refund policy or any rendered copy.
- Keep existing action availability truthful: a browser button can remain disabled or guarded; CSS must not make a canonical write look locally available.
- All selectors must begin at `.portal-page.portal-admin-runtime`, use portal tokens only, preserve semantic statuses and keyboard-visible focus, collapse intentionally at 980px/700px and respect reduced motion.

### Task 1: Add a failing Runtime presentation contract

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_runtime_final_surface_keeps_queue_actions_truthful`

- [x] **Step 1: Update the existing Audit assertion and write the Runtime red test**

Change the Audit contract from an exact one-branch string to these durable assertions:

```python
assert 'module === "audit"' in renderer_source
assert '" portal-admin-audit"' in renderer_source
assert '<article class="portal-page${pageClass}">' in renderer_source
```

Add the Runtime test which requires:

```python
assert 'module === "runtime"' in renderer_source
assert '" portal-admin-runtime"' in renderer_source
layer = re.search(
    r"/\* Final light Admin Runtime surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-admin-runtime"
```

With `_parse_css_rules` and `_css_declarations_for`, require tokenized root, guard, queue cards, job table cells, table action region, quiet/disabled controls, focus ring and `processing`/`completed`/`guarded`/`failed` badges. Reject selector leakage with `re.compile(rf"{re.escape(root_scope)}(?:$|(?=[\s>+~:#.\[]))")`, raw colors, RGB/HSL, gradients, `transparent`, non-portal variables and custom variables. Require base, 980px, 700px and reduced-motion groups only.

- [x] **Step 2: Prove red**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_runtime_final_surface_keeps_queue_actions_truthful
```

Expected: `FAIL` because Runtime has no route class and no final Runtime layer.

### Task 2: Add the smallest Runtime presentation surface

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_runtime_final_surface_keeps_queue_actions_truthful`

- [x] **Step 1: Extend only the route class mapping**

Replace the existing Audit-only expression with:

```javascript
const pageClass = module === "audit"
  ? " portal-admin-audit"
  : (module === "runtime" ? " portal-admin-runtime" : "");
```

Keep the existing `<article class="portal-page${pageClass}">` return and every other expression byte-for-byte unchanged.

- [x] **Step 2: Append route-scoped CSS**

Append `/* Final light Admin Runtime surface */`. Style the route root, guarded introduction, work-grid cards, runtime table, row metadata, action controls, quiet buttons, disabled state, semantic badges and focus with portal tokens. The action region must remain visually quiet and disabled controls must retain muted/soft styling; no selector may enable or conceal a confirmation/guard.

- [x] **Step 3: Add responsive and motion rules**

```css
@media (max-width: 980px) {
  .portal-page.portal-admin-runtime .portal-work-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 700px) {
  .portal-page.portal-admin-runtime :is(.portal-button--primary, .portal-button--quiet, .portal-data-table .portal-button) {
    min-height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .portal-page.portal-admin-runtime :is(.portal-card, .portal-metric, .portal-data-table tbody tr, .portal-button) {
    transition: none;
    transform: none;
  }
}
```

- [x] **Step 4: Prove green**

Run the Task 1 command again. Expected: `1 passed`.

### Task 3: Preserve canonical Runtime authority and hand off

**Files:**

- Test: `tests/test_admin_erp_navigation.py`
- Test: `tests/test_admin_erp_navigation_portal_contracts.py`
- Test: `tests/test_portal_safety_contracts.py`

- [x] **Step 1: Run focused regression**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_admin_erp_navigation.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_safety_contracts.py
```

Expected: all pass; Retry/Refund remain canonical, confirmation-gated and no browser runtime control appears.

- [x] **Step 2: Verify diff boundary**

```powershell
git diff --check
git diff -- static/portal/integration.js app.py copyfast_auth.py copyfast_bridge.py
```

Expected: clean; the authority and integration files named above have no diff.

- [x] **Step 3: Commit**

```powershell
git add static/portal/portal.js static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-runtime-light-surface.md
git commit -m "Polish Admin Runtime light surface"
```

## Self-review

- Audit keeps `portal-admin-audit` after the mapping extension; Runtime alone receives `portal-admin-runtime`.
- The UI stays a read/proposal surface and never claims live execution, repairs or provider control.
- CSS contracts lock status visibility, focus, disabled controls, responsive collapse, reduced motion, cascade scope and portal-only tokens.
