# Workboard Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Workboard routes readable, compact and professional in the teal/cyan light system without changing its signed workflow behavior.

**Architecture:** Append one final CSS-only Workboard layer after existing final-light surfaces. It scopes visual overrides to the three Workboard route classes and reuses only `--portal-*` tokens, leaving renderer, API, persistence, workflow state and truthfulness unchanged. A static contract proves the layer stays bounded, accessible and mobile-safe.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Lock the Workboard visual contract before the implementation

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Write the failing static contract**

Add `test_light_workboard_final_surface_keeps_lifecycle_workspace_readable`. It must find `/* Final light Workboard surface */`, capture only that layer through the next `/* Final light ... */` marker or EOF, and require the following literal CSS evidence:

```python
required = (
    ".portal-workboard",
    ".portal-workboard-new",
    ".portal-workboard-detail",
    ".portal-workboard-tabs",
    ".portal-workboard-column",
    ".portal-workboard-card",
    ".portal-workboard-reference-picker",
    ".portal-workboard-events",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

The contract must reject raw hex (`#[0-9a-fA-F]{3,8}`), `rgba(`, `linear-gradient`, `radial-gradient`, and custom properties outside the `--portal-` namespace. Update the preceding Asset Vault extractor to stop at the next final-light marker rather than `\\Z`.

- [ ] **Step 2: Run the focused contract and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: the new test fails because `Final light Workboard surface` is absent; existing contracts may remain green.

### Task 2: Add the final light Workboard CSS layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Append the bounded CSS layer**

Append `/* Final light Workboard surface */` after every existing final-light layer. Scope every selector under:

```css
.portal-page:is(.portal-workboard, .portal-workboard-new, .portal-workboard-detail)
```

Use only `--portal-*` colors and existing layout primitives. Cover tabs; overview/detail summaries and metric rows; kanban columns/cards, priorities, references and list rows; filters and pagination; editor/guide/reference-picker; lifecycle/checklist/version-event/schedule regions; archived and guarded states; focus-visible controls; non-shifting hover states; and the `700px` one-column collapse with 44px interactive controls. Do not edit the Workboard renderer, routes, API, database behavior, payment/provider behavior or Bot code.

- [ ] **Step 2: Run the focused contract and verify GREEN**

Run the same command from Task 1. Expected: all UI-foundation contracts pass.

### Task 3: Verify existing Workboard behavior remains intact

**Files:**
- Test: `tests/test_workboard_portal_contracts.py`
- Test: `tests/test_workboard_schedule_intents.py`
- Test: `tests/test_workboard_history_pagination.py`

- [ ] **Step 1: Run workflow contracts**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_workboard_portal_contracts.py tests\test_workboard_schedule_intents.py tests\test_workboard_history_pagination.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all commands pass. The feature remains UI-only and does not generate or alter any Workboard data.

- [ ] **Step 2: Commit the focused change**

Run:

```powershell
git add docs/superpowers/plans/2026-07-31-workboard-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Workboard light workspace surface"
```
