Exit code: 0
Wall time: 1.5 seconds
Output:
# First-run Workspace Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed first-run Workspace Setup and Starter Kits journey a calm, aligned teal/cyan light application surface without changing its server-owned setup, catalog, confirmation, or idempotency behavior.

**Architecture:** Append one token-only final CSS layer scoped to `.portal-page:is(.portal-workspace-setup, .portal-starter-kits)`. Preserve the existing renderer in `static/portal/portal.js`, signed-session ownership checks, CSRF, setup revision, Starter Kit confirmation, idempotency receipt, route resolution, Bot boundaries, PayOS, providers and jobs. The shared motion foundation stays progressive enhancement; this slice must remain fully usable with reduced motion.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS.

---

### Task 1: Pin the final-surface contract before styling it

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Read: `tests/test_workspace_setup_profile_portal_contracts.py`
- Read: `tests/test_workspace_starter_kits_portal_contracts.py`
- Read: `static/portal/portal.js:23196-23300`

- [ ] **Step 1: Write the failing test**

Add `test_light_first_run_workspace_final_surface_keeps_setup_and_starter_kits_clear`. It must isolate CSS after `/* Final light First-run Workspace surface */`, require root scope `.portal-page:is(.portal-workspace-setup, .portal-starter-kits)`, and parse rule declarations rather than only searching substrings.

Require these rule/declaration pairs:

```python
assert "background: var(--portal-surface-light);" in declarations_for(f"{root_scope} .portal-workspace-setup-form")
assert "transform: none;" in declarations_for(f"{root_scope} .portal-workspace-setup-focus-card:is(:hover, :focus-within)")
assert "background: var(--portal-light-accent-soft);" in declarations_for(f"{root_scope} .portal-workspace-setup-focus-card:has(input:checked)")
assert "opacity: 0.64;" in declarations_for(f"{root_scope} .portal-workspace-setup-focus-card:has(input:disabled)")
assert "background: var(--portal-surface-light);" in declarations_for(f"{root_scope} .portal-starter-kit-card")
assert "transform: none;" in declarations_for(f"{root_scope} .portal-starter-kit-card:is(:hover, :focus-within)")
assert "background: var(--portal-surface-soft);" in declarations_for(f"{root_scope} .portal-starter-kit-counts > div")
assert "outline: 3px solid var(--portal-focus) !important;" in declarations_for(f"{root_scope} :is(button, a, input, select, textarea):focus-visible")
```

Also require scoped `@media (max-width: 980px)`, `@media (max-width: 700px)`, and `@media (prefers-reduced-motion: reduce)` blocks. At 700px assert one-column selection/card grids and 44px touch targets; under reduced motion assert both `transition: none` and `transform: none`. Reject raw hex/rgb/hsl/gradients/`transparent`, non-`--portal-*` variables, and selectors outside the root scope.

- [ ] **Step 2: Run the focused test to verify RED**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k first_run_workspace_final_surface -p no:cacheprovider --basetemp C:\tmp\copyfast247-red
```

Expected: `1 failed` because the final marker and rule layer do not exist.

### Task 2: Add only the scoped final visual layer

**Files:**
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Append the final CSS marker and root scope**

Append `/* Final light First-run Workspace surface */` after the prior final layers. Use only `.portal-page:is(.portal-workspace-setup, .portal-starter-kits)` and `--portal-*` semantic tokens.

- [ ] **Step 2: Normalize Workspace Setup without changing its form or action attributes**

Use light working surfaces for the step rail, account context and form; soft surfaces for account metadata and studio icon cells. Preserve visual selection with an accent-soft checked card, a sky focus outline, stationary hover/focus styles, and visibly unavailable disabled cards. Do not edit `renderWorkspaceSetup`, fields, selection-limit logic, save/skip actions or labels.

- [ ] **Step 3: Normalize Starter Kit catalog, detail and guarded/loading states**

Use light surfaces for cards, detail, confirmation, scope rail and empty states; soft surfaces for count tiles, confirmation checks and icon cells. Preserve receipt/confirmation copy, apply/refresh attributes, idempotency, availability and guarded behavior. Do not edit `renderStarterKitCatalog`, `renderStarterKitDetail`, `renderStarterKits`, route keys or API calls.

- [ ] **Step 4: Preserve responsive and reduced-motion behavior**

At 980px stack the Starter Kit scope below the catalog. At 700px use one column for steps, form fields, studio choices and kit cards; retain 44px controls and two-column count tiles. Under reduced motion remove cosmetic transitions and transforms from cards, controls and selection cards.

- [ ] **Step 5: Run the focused test to verify GREEN**

Run the Task 1 command again. Expected: `1 passed`.

### Task 3: Repair the verified first-run portal allowlist gap

**Files:**
- Modify: `tests/test_workspace_setup_profile_portal_contracts.py`
- Modify: `copyfast_registry.py`
- Read: `copyfast_pages.py:336-346`

- [ ] **Step 1: Write the failing route test**

Add a behavior-level contract that requires both `/workspace/setup` and
`/starter-kits` to be in `copyfast_registry.allowed_paths()`, then renders
`/workspace/setup`, `/starter-kits` and one fixed valid Starter Kit detail
with `copyfast_pages.render_portal(..., interface_locale="vi")`. Each response
must be `200` and contain the Portal bootstrap. Do not allow an arbitrary
Starter Kit slug.

- [ ] **Step 2: Verify RED**

Run the new test alone. Expected: it fails because `/workspace/setup` is not
currently in the server-side signed Web portal allowlist, even though its
renderer and API exist.

- [ ] **Step 3: Apply the smallest allowlist correction**

Add only the reviewed Web-owned first-run base paths to the explicit static
set returned by `allowed_paths()`. Do not add a new capability, menu item,
role, API route, unauthenticated bypass, provider, Bot bridge, payment or
session behavior.

- [ ] **Step 4: Verify GREEN**

Run the route test again, then verify unauthenticated access still follows the
existing signed-session redirect behavior.

### Task 4: Verify focused scope and commit

**Files:**
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_workspace_setup_profile_portal_contracts.py`
- Test: `tests/test_workspace_starter_kits_portal_contracts.py`
- Modify: `copyfast_registry.py`

- [ ] **Step 1: Run focused UI and workflow contracts**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_workspace_setup_profile_portal_contracts.py tests/test_workspace_starter_kits_portal_contracts.py -p no:cacheprovider --basetemp C:\tmp\copyfast247-focused
git diff --check
```

Expected: the focused suite passes and the diff is whitespace-clean.

- [ ] **Step 2: Browser smoke**

Use a signed fixture account to visit `/workspace/setup`, save a setup choice, open `/starter-kits`, open one kit detail and return. Check desktop and mobile layouts without submitting a provider, payment or Bot action.

- [ ] **Step 3: Review final scope and commit**

Confirm only this plan, `static/portal/portal-theme.css`,
`tests/test_teal_cyan_ui_foundation_contracts.py`,
`tests/test_workspace_setup_profile_portal_contracts.py`, and
`copyfast_registry.py` changed; then run:

```powershell
git add copyfast_registry.py static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py tests/test_workspace_setup_profile_portal_contracts.py docs/superpowers/plans/2026-07-31-first-run-workspace-light-surface.md
git commit -m "Polish first-run workspace light surface"
```
