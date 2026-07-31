# Support Desk Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make customer Support Desk and separately protected internal CSKH Support Desk legible, compact and cohesive in the teal/cyan light system without changing case, evidence or recovery semantics.

**Architecture:** Append one CSS-only final layer scoped to the existing customer and internal Support route classes. It retains the current signed-session and role gates, public/internal message separation, evidence redaction, confirmation and revision behavior; no renderer, API, provider, payment, Bot or customer data changes are in scope.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Add a failing Support Desk final-surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Add the static contract**

Add `test_light_support_desk_final_surface_keeps_customer_and_operator_cases_readable`. It must find `/* Final light Support Desk surface */`, capture only that layer through the next final-light marker or EOF, and require:

```python
required = (
    ".portal-support-desk",
    ".portal-support-cases",
    ".portal-support-case-detail",
    ".portal-support-admin",
    ".portal-support-admin-case-detail",
    ".portal-support-intro",
    ".portal-support-case-hero",
    ".portal-support-case-card",
    ".portal-support-recovery",
    ".portal-support-message",
    ".portal-support-advisor",
    ".portal-support-consultation",
    ".portal-support-filter",
    ".portal-support-care-lane",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

Reject raw hex, `rgba(`, gradients and non-`--portal-*` custom variables. Update the preceding Memory/Prompt extractor to stop at the next final-light marker.

- [ ] **Step 2: Run RED**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\support-237-foundation-qa tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: only the new support final-layer contract fails for the missing marker.

### Task 2: Implement the light Support Desk layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Add the bounded CSS layer**

Scope all selectors under:

```css
.portal-page:is(.portal-support-desk, .portal-support-cases, .portal-support-case-detail, .portal-support-admin, .portal-support-admin-case-detail)
```

Use `--portal-*` tokens only. Cover customer/admin intro and case hero metrics; customer intake/boundary/advisor/consultation; case grid, category, metadata, pagination and activity; recovery states; public/operator/internal message thread treatment without exposing more information; internal CSKH filters, care board/lanes and admin forms; guarded/disabled state; focus-visible and non-shifting hover. At `700px`, collapse forms/cards/grids safely and make controls at least 44px. Do not use or change customer data, browser role state, evidence data, provider, wallet, PayOS, Bot, API or routes.

- [ ] **Step 2: Run GREEN**

Run the same command from Task 1. Expected: all foundation contracts pass.

### Task 3: Verify support privacy/role behavior and commit

**Files:**
- Test: `tests/test_support_portal_contracts.py`
- Test: `tests/test_support_care_portal_contracts.py`
- Test: `tests/test_support_evidence_portal_contracts.py`
- Test: `tests/test_support_recovery_read_model_contracts.py`
- Test: `tests/test_support_resolution_feedback_portal_contracts.py`

- [ ] **Step 1: Run targeted verification**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\support-237-contract-qa tests\test_support_portal_contracts.py tests\test_support_care_portal_contracts.py tests\test_support_evidence_portal_contracts.py tests\test_support_recovery_read_model_contracts.py tests\test_support_resolution_feedback_portal_contracts.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all commands pass. The UI layer never creates, changes or exposes a case, message, receipt, evidence, payment, provider job or Bot record.

- [ ] **Step 2: Commit**

```powershell
git add docs/superpowers/plans/2026-07-31-support-desk-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Support Desk light workspace surface"
```
