# Delivery Center Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed Delivery Center (`/jobs`, `/jobs/{id}`, `/assets`)
clear, balanced and responsive on the existing teal/cyan light application
system without changing truthful job, output or delivery behavior.

**Architecture:** Add a presentation-only `.portal-delivery-page` class to the
three existing renderer roots, then append one final token-only CSS layer
scoped to `.portal-page.portal-delivery-page`. The shared route strip may also
be styled for the existing `.portal-asset-vault` root, but the renderer and
vault page themselves remain untouched. Static pytest contracts parse only the
new final layer. No endpoint, request, canonical data source, signed URL,
Core Bridge, Bot, PayOS, wallet, provider or job state changes.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript renderer, static CSS,
Python `pytest` contracts.

---

## File map

- Modify: `static/portal/portal.js` — add a visual root class only to Jobs,
  Job detail and Assets renderer roots.
- Modify: `static/portal/portal-theme.css` — append the scoped final light
  Delivery Center layer.
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — add the
  declaration-level red/green contract.
- Create: `docs/superpowers/specs/2026-07-31-delivery-center-light-surface-design.md`
  — visual and authority scope.
- Create: `docs/superpowers/plans/2026-07-31-delivery-center-light-surface.md`
  — this implementation record.

### Task 1: Add the red delivery-surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Read: `tests/test_delivery_center_record_identity_contracts.py`
- Read: `tests/test_delivery_navigation_app_ux_contracts.py`
- Read: `tests/test_asset_vault_lifecycle.py`
- Read: `tests/test_portal_safety_contracts.py`

- [x] **Step 1: Write one failing contract test**

Add `test_light_delivery_center_final_surface_keeps_canonical_states_clear`.
Require all three renderers to contain the exact root markup:

```python
assert PORTAL_CLIENT.count(
    '<article class="portal-page portal-delivery-page">'
) == 3
```

Extract only this CSS layer and parse it with the existing helpers:

```python
layer = re.search(
    r"/\\* Final light Delivery Center surface \\*/(?P<css>.*?)(?=/\\* Final light [^*]*\\*/|\\Z)",
    PORTAL_THEME.read_text(encoding="utf-8"),
    flags=re.DOTALL,
)
assert layer is not None
delivery_css = layer.group("css")
rules = _parse_css_rules(delivery_css)
root_scope = ".portal-page.portal-delivery-page"
```

Require declarations for the delivery summary/card/read-status, exact
semantic `reported`, `pending`, `validated`, `unavailable` and `vault`
states, a stationary filter/card hover, the `3px` focus ring, a `980px`
single-column work grid, a `700px` three-column delivery-nav grid with
`overflow-x: visible` and `scroll-snap-type: none`, `44px` controls, and
reduced-motion `transition: none` / `transform: none` declarations. Require
all final selectors to begin with either the delivery root or:

```python
shared_nav_scope = ".portal-page:is(.portal-delivery-page, .portal-asset-vault)"
```

Reject raw hex, rgb/hsl, gradients, `transparent`, and any `var(--*)` token
outside the `--portal-*` namespace.

- [x] **Step 2: Run RED and confirm the cause**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k delivery_center_final_surface -p no:cacheprovider --basetemp C:\tmp\copyfast249-red
```

Expected: one assertion failure because neither the final CSS marker nor the
three delivery root classes exist. Do not change production code if the test
fails for another reason.

Verification record: a test-constant typo was corrected without changing
production code. The red run then failed for the required missing
`portal-delivery-page` class (`1 failed, 80 deselected`).

### Task 2: Implement the smallest route-local presentation layer

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Add only the renderer class**

Change the return root in `renderJobs`, `renderJobDetail` and `renderAssets`
from:

```javascript
return `<article class="portal-page">${renderHero(page, context)}...`
```

to:

```javascript
return `<article class="portal-page portal-delivery-page">${renderHero(page, context)}...`
```

Do not alter `renderAssetVault`, markup order, route values, state functions,
controls, links, form fields, `data-*` attributes or copy.

- [x] **Step 2: Append the final token-only layer**

Append `/* Final light Delivery Center surface */` after the current final
light layer. Every route-specific selector begins with
`.portal-page.portal-delivery-page`. The only shared selector begins with
`.portal-page:is(.portal-delivery-page, .portal-asset-vault)` and targets
`.portal-delivery-nav` / its links.

Use existing portal tokens to normalize summary cards, delivery center cards,
read status, lifecycle rows, next-action panel, tables/mobile records,
filters, empty/guarded panels and semantic delivery states. Preserve the
semantic distinction among `reported`, `pending`, `validated`, `unavailable`
and `vault`. Hover and focus styles must be stationary.

- [x] **Step 3: Add responsive and accessibility rules**

At `max-width: 980px`, set `.portal-work-grid` to a single column. At
`max-width: 700px`, set the shared delivery nav to a three-column grid with
`overflow-x: visible`, no snap behavior, normal link wrapping and `44px`
height; collapse delivery fact grids/records to one column. Add a `3px`
focus-visible outline and a reduced-motion branch that disables cosmetic
transitions/transforms.

- [x] **Step 4: Verify GREEN**

Run the Task 1 command again. Expected: the new contract passes without
changing job, delivery or asset behavior.

Verification record: `1 passed, 80 deselected`.

### Task 3: Verify truth, ownership and UI scope

**Files:**
- Test: `tests/test_delivery_center_record_identity_contracts.py`
- Test: `tests/test_delivery_navigation_app_ux_contracts.py`
- Test: `tests/test_asset_vault_lifecycle.py`
- Test: `tests/test_portal_safety_contracts.py`

- [x] **Step 1: Run the focused regression suite**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_delivery_center_record_identity_contracts.py tests/test_delivery_navigation_app_ux_contracts.py tests/test_asset_vault_lifecycle.py tests/test_portal_safety_contracts.py -p no:cacheprovider --basetemp C:\tmp\copyfast249-focused
git diff --check
```

Expected: all runnable tests pass; the Web continues to distinguish canonical
job metadata, output metadata, owner-scoped delivery and Web Vault records.

Verification record: `177 passed in 38.91s` in a fresh focused run.

- [x] **Step 2: Confirm scope mechanically**

```powershell
git diff --name-only origin/main...HEAD
```

Expected: only the two documentation files, `portal.js`, `portal-theme.css`
and the UI foundation contract are changed. `copyfast_api.py`,
`copyfast_bridge.py`, payment, webhook, provider, job engine and `bot.py`
must be absent.

Verification record: the uncommitted implementation diff contains only
`portal.js`, `portal-theme.css`, the UI contract and this plan/design record.
`git diff --check` is clean and `node --check static/portal/portal.js` exits
`0`.

### Task 4: Safe visual smoke, review and sequential handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-07-31-delivery-center-light-surface-design.md`
- Modify: `docs/superpowers/plans/2026-07-31-delivery-center-light-surface.md`

- [x] **Step 1: Attempt a read-only local browser smoke**

Use the local FastAPI server only. Confirm anonymous `/jobs` redirects to
`/login?next=/jobs`; do not create a job, upload/download a file, refresh a
record, submit a ticket, invoke provider/billing or change data. If a signed
local browser session can attach, inspect `/jobs`, `/jobs/{safe-test-id}` and
`/assets` at desktop and 375px. Record an attachment limitation instead of
claiming a private-route visual pass.

Verification record: no local application listener was active on the usual
development ports and no signed browser session was available. No local server
was started, no data was created, and no private-route visual pass is claimed.

- [x] **Step 2: Request two-stage review**

First run spec compliance review against this plan. Once approved, run code
quality review for selector ownership, token-only scope, test strength and
non-functional renderer class changes. Address every finding and re-review
before commit.

Verification record: independent spec review approved renderer scope,
`renderAssetVault` non-change, marker, tokens, semantic states, focus,
responsive behavior and reduced motion. Independent code-quality review found
no actionable scope or cascade issue.

- [ ] **Step 3: Commit the isolated slice**

```powershell
git add static/portal/portal.js static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/specs/2026-07-31-delivery-center-light-surface-design.md docs/superpowers/plans/2026-07-31-delivery-center-light-surface.md
git commit -m "Polish Delivery Center light workspace surface"
```

Expected: one UI-only commit. Push one branch, open one PR, wait for green
checks and merge sequentially. Do not manually deploy Railway for this
presentation-only slice.
