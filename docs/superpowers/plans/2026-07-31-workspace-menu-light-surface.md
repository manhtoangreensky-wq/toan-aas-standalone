# Workspace Menu Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the signed customer Workspace Menu into a compact, readable teal/cyan directory that keeps every navigation, guarded state and server authority boundary truthful.

**Architecture:** Append one final CSS-only layer to `static/portal/portal-theme.css`, scoped exclusively to `.portal-page.portal-workspace-menu`. The layer overrides legacy translucent/dark child surfaces after the canonical teal/cyan theme loads, while preserving `portal.js` rendering, signed-session checks, route manifests, capability states and all server APIs.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Lock the Workspace Menu light-surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Add the failing final-layer test**

Add `test_light_workspace_menu_final_surface_keeps_customer_directory_readable`.
It finds `/* Final light Workspace Menu surface */`, captures only through the
next final-light marker or EOF, and requires:

```python
required = (
    ".portal-workspace-menu",
    ".portal-workspace-menu-intro",
    ".portal-workspace-menu-intro-status",
    ".portal-workspace-menu-directory",
    ".portal-workspace-menu-group",
    ".portal-workspace-menu-group-head",
    ".portal-workspace-menu-grid",
    ".portal-workspace-menu-card",
    ".portal-workspace-menu-card-copy",
    ".portal-workspace-menu-card-state",
    ".portal-workspace-menu-card-footer",
    ".portal-workspace-menu-boundary",
    ".portal-workspace-menu-boundary-list",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

Use the existing nested-media selector extractor (rename it to a neutral
`_final_light_layer_selectors` during refactor) to require every selector to
contain `.portal-page.portal-workspace-menu`. Reject raw hex, `rgb()`/`hsl()`
values, all linear/radial/conic gradients and custom variables outside
`--portal-*`.

- [x] **Step 2: Run RED**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\workspace-menu-239-red tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: only the new Workspace Menu contract fails because the final-layer
marker does not yet exist.

### Task 2: Add the scoped Workspace Menu light layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [x] **Step 1: Append token-only CSS below the current final-light layers**

Scope every selector under `.portal-page.portal-workspace-menu`. Use only
`--portal-*` values and cover the intro/status, directory groups/count, card
surface/icon/copy/state/footer, boundary list and focus treatment. For card
hover/focus, keep border/background feedback but set `transform: none` and
`box-shadow: none` so navigation never shifts vertically. Keep a guarded
capability visibly guarded; do not add a disabled browser shortcut, inferred
role or fake workflow status.

At `700px`, collapse the Workspace Menu grid and boundary list to one column,
stack the group header safely and keep shared interactive controls at least
44px high. Do not modify `portal.js`, routes, locale copy, motion utility,
auth/session checks, Core Bridge, wallet, PayOS, providers, Bot or data.

- [x] **Step 2: Run GREEN**

Run the Task 1 command. Expected: all UI foundation contracts pass.

### Task 3: Verify customer navigation stays behavioral-only

**Files:**
- Test: `tests/test_workspace_menu_portal_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Run targeted checks**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\workspace-menu-239-contract tests\test_teal_cyan_ui_foundation_contracts.py tests\test_workspace_menu_portal_contracts.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: the directory remains private/PWA-excluded, links remain navigation
only, and no CSS change can grant a role, fabricate capability readiness or
start a provider/payment/Bot action.

### Task 4: Commit the isolated surface

**Files:**
- Modify: `docs/superpowers/plans/2026-07-31-workspace-menu-light-surface.md`
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `static/portal/portal-theme.css`

- [x] **Step 1: Commit after the targeted checks are green**

```powershell
git add docs/superpowers/plans/2026-07-31-workspace-menu-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Workspace Menu light directory"
```
