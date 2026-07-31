# Data Controls Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the light teal/cyan presentation of signed Data Controls without changing export, erasure-review, cancellation, identity verification, ownership, revision, or audit behavior.

**Architecture:** Append a root-scoped CSS layer and test it statically. Existing Data Controls routes and forms remain authoritative server-side controls; the browser continues to show truthful guarded, pending and read-only states only.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS.

---

### Task 1: Pin the final Data Controls visual boundary

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `static/portal/portal-theme.css`
- Read: `tests/test_copyfast_data_controls.py`
- Read: `tests/test_data_controls_portal_contracts.py`

- [ ] **Step 1: Write the failing test**

Add `test_light_data_controls_final_surface_keeps_review_boundary_clear`. It must require `/* Final light Data Controls surface */`, root scope `.portal-page.portal-account-data-controls`, and style coverage for settings nav, `.portal-support-intro`, `.portal-state`, `.portal-panel-row`, `.portal-project-steps`, `.portal-notice`, `.portal-checkbox`, quiet actions, disabled/focus-visible state, `@media (max-width: 980px)`, `@media (max-width: 700px)`, `@media (prefers-reduced-motion: reduce)` and a 44px touch target. Assert every parsed selector starts with root scope and the final layer contains no raw hex, `rgb`/`hsl`, gradients, `transparent`, or non-`--portal-*` token.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k data_controls_final_surface -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast244-red
```

Expected: `1 failed` because the final-light marker is absent.

- [ ] **Step 3: Add only scoped visual CSS**

Append the marker and root-scoped rules in `static/portal/portal-theme.css`. Use only `.portal-page.portal-account-data-controls` selector branches and semantic portal tokens. Set support/state panels onto the light surface (including required `!important` state override), make review rows, scopes and checkbox clear, retain warning/guarded cues, preserve disabled forms, visible focus, 980/700px layouts and reduced motion. Do not edit JS, API, server data-controls code, Bot, payment, provider, storage, or form actions.

- [ ] **Step 4: Run test to verify it passes**

Run the red command again. Expected: `1 passed`.

- [ ] **Step 5: Run critical safety checks**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_copyfast_data_controls.py tests/test_data_controls_portal_contracts.py tests/test_account_security_app_ux_contracts.py -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast244-focused
git diff --check
```

Expected: all selected tests pass and the diff is whitespace-clean.

- [ ] **Step 6: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-07-31-data-controls-light-surface.md
git commit -m "Polish data controls light surface"
```
