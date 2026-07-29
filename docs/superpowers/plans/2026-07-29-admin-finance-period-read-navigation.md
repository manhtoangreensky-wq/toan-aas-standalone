# Admin Finance Period Read Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let eleven reviewed frozen Bot Finance menu literals open only a fresh signed-admin `/admin/finance` read route without replaying Bot financial state.

**Architecture:** Extend the existing exact private Admin ERP navigation registry. Every descriptor has a fixed target, `admin` classification, `SIGNED_CANONICAL_ADMIN_READ`, `WEB_NAVIGATION`, and no-transfer dispositions. The generic `menu|*` fallback continues to reject every value outside the finite raw-key list.

**Tech Stack:** Python static AST audit, pytest, generated Markdown/JSON migration evidence.

---

### Task 1: Write the red Finance menu contract

**Files:**
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the eleven exact expected descriptors to `test_static_audit_keeps_admin_erp_menu_navigation_private_and_exact`.**

```python
finance_period_navigation = {
    "menu|finance_overview",
    "menu|finance_revenue",
    "menu|finance_revenue_this_month",
    "menu|finance_revenue_last_month",
    "menu|finance_revenue_year",
    "menu|finance_expense_this_month",
    "menu|finance_expense_last_month",
    "menu|finance_expense_year",
    "menu|finance_profit_this_month",
    "menu|finance_profit_year",
    "menu|finance_export_month",
    "menu|finance_export_year",
}
```

For every descriptor, require target `/admin/finance`, `NAVIGATION_ONLY`, `SIGNED_CANONICAL_ADMIN_READ`, `WEB_NAVIGATION`, `BOT_ADMIN_ONLY`, no Bot finance data/period/export transfer, no provider/wallet/PayOS action, and `NO_RUNTIME_CLAIM`.

- [ ] **Step 2: Add boundary cases.**

Require `MENU|FINANCE_OVERVIEW`, `menu|finance_revenue_year|future`, `menu|finance_revenue_custom_help`, `menu|finance_compliance`, `menu|finance_compliance_update`, `menu|tax_estimate`, and `menu|tax_export_month` to remain `MENU_SOURCE_REVIEW_REQUIRED` with `NEEDS_FEATURE_DISPOSITION`.

- [ ] **Step 3: Run the focused test red.**

Run: `python -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_admin_erp_menu_navigation_private_and_exact`

Expected: FAIL because the eleven descriptors do not exist yet.

### Task 2: Implement exact read-navigation evidence

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Regenerate: `docs/migration/*`, `reports/migration/*`

- [ ] **Step 1: Add the eleven raw descriptors to `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS`.**

Each descriptor uses the existing `/admin/finance` `admin_finance` metadata and a source-specific no-transfer disposition. Do not lower/casefold/split/prefix-match source keys.

- [ ] **Step 2: Update generated Admin ERP and menu contract wording.**

Describe the entries as fresh Finance reads. State that no Bot data, selected period, export command/file, calculation, tax/compliance or write authority transfers, and every unlisted finance/tax action remains source-review-required.

- [ ] **Step 3: Run the focused test green and regenerate frozen evidence.**

```powershell
python scripts/migration/audit_bot_to_web.py --bot-root C:\Users\toann\Documents\Codex\2026-05-31\files-mentioned-by-the-user-bot\toanaas-hotfix-28ff87f --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: the exact eleven new literals have `NAVIGATION_ONLY`; all boundary cases remain fail-closed.

### Task 3: Verify and integrate

**Files:**
- Verify: static auditor, migration tests, Finance portal contracts and generated evidence.

- [ ] **Step 1: Synchronize `docs/migration/TEST_EVIDENCE.md` from regenerated reports.**

- [ ] **Step 2: Run `pytest -q tests/test_migration_audit.py tests/test_finance_planning_portal_contracts.py`, compileall, Node syntax checks and `git diff --check`.**

- [ ] **Step 3: Stage only task files, inspect staged scope, review, commit, push, PR, merge only after a green GitHub gate, and verify Railway deployment plus `/health`.**
