# Account Activity Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed `/account/activity` activity log consistent with the light teal/cyan workspace without changing its owner-scoped, sanitized-data boundary or refresh behavior.

**Architecture:** Add a final root-scoped CSS layer and a static contract only. The renderer, `refresh-account-activity` action, rows table, session rules and activity-source boundary remain exactly as they are.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS.

---

### Task 1: Pin a light, owner-scoped activity-log surface

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `static/portal/portal-theme.css`
- Read: `tests/test_portal_safety_contracts.py`

- [ ] **Step 1: Write the failing test**

Add `test_light_account_activity_final_surface_keeps_owner_scoped_log_clear`. It must search for `/* Final light Account Activity surface */`, require root scope `.portal-page.portal-account-activity`, and require scoped styling for `.portal-settings-nav`, `.portal-campaign-boundary`, `.portal-state`, `.portal-state-meta`, `.portal-data-table`, `.portal-inline-actions`, `.portal-notice`, `.portal-button--quiet`, disabled/focus-visible behavior, `@media (max-width: 700px)`, and `@media (prefers-reduced-motion: reduce)`. Assert each parsed selector starts with the root scope and the layer contains no raw hex, `rgb`/`hsl`, gradients, `transparent`, or non-`--portal-*` token.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k account_activity_final_surface -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast243-red
```

Expected: `1 failed` because the final-light marker does not exist.

- [ ] **Step 3: Add only scoped visual CSS**

Append the marker and styles in `static/portal/portal-theme.css`. Use only selectors beginning `.portal-page.portal-account-activity` and `--portal-*` values. Set the boundary/state surfaces to light with the required `!important` override for `.portal-state`; style table header/cells, metadata chips, notices, quiet refresh/account actions, disabled controls and focus ring. At `700px`, keep controls at least 44px and preserve table readability; under reduced motion, disable only the layer's transitions. Do not modify renderer, integration, route, API, account data, Bot/PayOS/provider code, or action behavior.

- [ ] **Step 4: Run test to verify it passes**

Run the red command again. Expected: `1 passed`.

- [ ] **Step 5: Run critical activity safety checks**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_portal_safety_contracts.py -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast243-focused
git diff --check
```

Expected: all selected tests pass and the diff is whitespace-clean.

- [ ] **Step 6: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-07-31-account-activity-light-surface.md
git commit -m "Polish account activity light surface"
```
