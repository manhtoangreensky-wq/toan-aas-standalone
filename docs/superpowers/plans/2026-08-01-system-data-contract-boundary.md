# System/Data Registry Boundary Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the stale System/Data static-test slice so it ends before the independently reviewed Billing registry, while preserving every migration action and its authority boundary.

**Architecture:** `SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS`, `BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS`, and `TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS` are three adjacent, separate registries. Change only the test delimiter/comment and assert the Billing entry is inside its own slice; do not alter the migration auditor, Bot inventory, routes, payment behavior or Web code.

**Tech Stack:** Python static contract test and migration inventory source.

---

## File structure

- Modify: `tests/test_system_data_stewardship_portal_contracts.py` — correct the registry boundary assertion.
- Create: `docs/superpowers/plans/2026-08-01-system-data-contract-boundary.md` — this execution record.

### Task 1: Correct the stale static delimiter

**Files:**

- Modify: `tests/test_system_data_stewardship_portal_contracts.py`
- Test: `tests/test_system_data_stewardship_portal_contracts.py::test_audit_contract_is_finite_and_keeps_payment_video_and_bot_state_out_of_browser`

- [x] **Step 1: Preserve the failing baseline evidence**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_system_data_stewardship_portal_contracts.py::test_audit_contract_is_finite_and_keeps_payment_video_and_bot_state_out_of_browser
```

Expected: `FAIL` because the old slice ends at Tax and incorrectly contains the distinct Billing registry.

- [x] **Step 2: Replace only the slice boundary and add the Billing proof**

Use the Billing registry as the System/Data end boundary and make the intended separation explicit:

```python
# System/Data ends before the separate Billing and Tax registries.
system_registry_slice = audit[
    audit.index("SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS"):
    audit.index("BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS")
]
billing_registry_slice = audit[
    audit.index("BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS"):
    audit.index("TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS")
]
assert '"menu|billing' not in system_registry_slice
assert '"menu|billing": {' in billing_registry_slice
assert '"menu|tax_' not in system_registry_slice
assert '"menu|video_' not in system_registry_slice
```

Do not modify `scripts/migration/audit_bot_to_web.py`.

- [x] **Step 3: Prove green and scope**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_system_data_stewardship_portal_contracts.py tests/test_migration_audit.py
git diff --check
git diff -- scripts/migration/audit_bot_to_web.py
```

Expected: all selected tests pass; no migration-source change exists.

- [x] **Step 4: Commit**

```powershell
git add tests/test_system_data_stewardship_portal_contracts.py docs/superpowers/plans/2026-08-01-system-data-contract-boundary.md
git commit -m "Fix System Data registry contract boundary"
```

## Self-review

- This is a test-boundary correction, not a billing or System/Data behavior change.
- The test now proves `menu|billing` belongs to the separate Billing registry and cannot leak into System/Data assertions.
- No Bot, payment, Web route, authority, provider or migration action is altered.
