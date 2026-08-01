# Reliability Follow-up Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed `/admin/reliability` follow-up queue dense, calm and legible as a light teal/cyan ERP surface, without altering acknowledgement, resolution, reopen, Support Desk handoff, authorization, confirmation, revision or idempotency behavior.

**Architecture:** Leave the Reliability renderer, action forms, integrations and API untouched. Add one token-only final CSS layer rooted at `.portal-page.portal-reliability-admin`, protected by a static visual contract. It styles only existing metadata rows, filters, cards, actions and truthful guarded states; it cannot claim the system auto-fixed an incident or expose sensitive signal data.

**Tech Stack:** FastAPI Portal shell, vanilla CSS in `static/portal/portal-theme.css`, existing JS renderer/action delegation, Python `pytest` static and authority contracts.

---

## File structure

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — scoped presentation contract only.
- Modify: `static/portal/portal-theme.css` — final Reliability route layer.
- Create: `docs/superpowers/plans/2026-08-01-admin-reliability-light-surface.md` — execution record.

## Design constraints

- Keep the high-trust ERP layout: light work surfaces, compact rows, aligned labels/actions and existing server-owned semantic statuses.
- Retain actual write affordances only where the server previously grants them; CSS must not reveal a disabled action as enabled or make metadata acknowledgment look like a code/provider/deploy fix.
- Existing form labels remain visible; filters are two columns on wide routes and one on mobile. Action controls stay 44px at mobile.
- `awaiting_confirm`/`processing` use info, `completed` success, `guarded` warning and `failed` danger; labels remain visible.
- No raw colors, gradients, `transparent`, non-portal variables, new motion, browser-side authority or CSS outside the Reliability root.

### Task 1: Establish a failing static presentation contract

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_reliability_followup_final_surface_keeps_actions_truthful`

- [x] **Step 1: Add the red test**

Extract `renderReliabilityAdmin` and assert its exact route class. Extract only the future layer:

```python
layer = re.search(
    r"/\* Final light Reliability Follow-up surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-reliability-admin"
```

Use existing CSS-parser helpers to require the root, intro, metrics, cards, filter, Reliability row, action container, quiet/disabled action states, focus ring and semantic badges. Require 980px one-column operations grid, 700px one-column metrics/filter with 44px actions, and reduced-motion. Assert every selector begins with the exact root, only empty/980/700/reduced at-rules exist, and raw colors/gradient/transparent/non-portal variables are forbidden.

- [x] **Step 2: Prove red**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_reliability_followup_final_surface_keeps_actions_truthful
```

Expected: missing final marker only.

### Task 2: Add the smallest route-scoped reliability layer

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_reliability_followup_final_surface_keeps_actions_truthful`

- [x] **Step 1: Append token-only CSS**

Append `/* Final light Reliability Follow-up surface */` after Automation Monitor. The root uses `--portal-ink` / `--portal-surface-light`. The intro and boundary use soft surface/border tokens; metrics/cards/rows use aligned light surfaces and borders; labels/support copy use muted ink; action wrappers remain stationary. Existing quiet actions stay quiet with a tokenized hover; disabled action elements remain visibly muted.

Style existing `portal-reliability-row`, `portal-reliability-copy`, `portal-reliability-meta`, `portal-reliability-actions`, `portal-support-filter`, `.portal-select`, `.portal-operations-boundary`, cards and badges only. Do not change HTML, event attributes, form submissions, hidden fields, route names, confirmation text, status mapping or any server request.

- [x] **Step 2: Add responsive/reduced-motion rules**

At 980px, make the Reliability route's `portal-operations-admin-grid` one column. At 700px, collapse the metrics and filter to one column and keep primary/quiet action controls at least 44px. At reduced motion, disable only this layer's transitions/transforms for cards, metrics, rows, filter controls and buttons.

- [x] **Step 3: Prove green**

Run Task 1's focused test. Expected: `1 passed`.

### Task 3: Verify action authority did not change

**Files:**

- Test: `tests/test_operations_reliability.py`
- Test: `tests/test_operations_reliability_portal_contracts.py`
- Test: `tests/test_operations_autopilot_portal_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`

- [x] **Step 1: Run focused regression**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_operations_reliability.py tests/test_operations_reliability_portal_contracts.py tests/test_operations_autopilot_portal_contracts.py tests/test_admin_erp_navigation.py
```

Expected: all tests pass; actions stay signed/CSRF/confirmation/revision/idempotency-protected and never become Bot/provider/PayOS/wallet/deploy behavior.

- [x] **Step 2: Verify scope**

```powershell
git diff --check
git diff -- static/portal/portal.js static/portal/integration.js app.py copyfast_operations_reliability.py copyfast_operations.py
```

Expected: clean whitespace and no behavior changes.

- [x] **Step 3: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-reliability-light-surface.md
git commit -m "Polish Reliability Follow-up light surface"
```

## Self-review

- This slice has one admin route and no new endpoint or capability.
- It reinforces the required distinction between metadata follow-up and an actual repair, preserving guarded states and all signed write gates.
- It is isolated from other Admin/customer routes via strict root-scoped selectors and from business logic via focused authority regression tests.
