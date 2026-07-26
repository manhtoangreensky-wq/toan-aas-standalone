# Admin Finance Expense Categories Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map static Bot-admin Finance Expense Categories to fresh Admin
Finance read navigation without transferring finance data or enabling category
or expense writes.

**Architecture:** Add one exact literal to the private Admin ERP registry.
Reuse the existing signed canonical-admin Finance page and keep finance data,
period, write, case-variant, suffix, and future callbacks source-review-only.

**Tech Stack:** Python 3.12, static source audit, FastAPI route inventory,
pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:155-176,1585-1800`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Move only Expense Categories into the expected private registry**

Add:

```python
"menu|finance_expense_categories": ("/admin/finance", "admin_finance"),
```

Remove this exact parent from older source-review assertions. Retain existing
per-entry target, authority, status, resolution, and private-metadata checks.

- [ ] **Step 2: Pin Categories dispositions and sensitive siblings**

Assert the descriptor contains:

```python
"BOT_FINANCE_EXPENSE_CATEGORIES_NOT_REPLAYED",
"NO_CANONICAL_FINANCE_DATA_TRANSFER",
"NO_FINANCE_PERIOD_OR_EXPENSE_PARAMETER_TRANSFER",
"NO_EXPENSE_WRITE_CATEGORY_OR_FILE_DELIVERY",
"NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
```

For each callback below, assert exactly `MENU_SOURCE_REVIEW_REQUIRED`,
`NEEDS_FEATURE_DISPOSITION`, and
`menu_callback_requires_finite_exact_web_contract`, with no Admin ERP
metadata:

```python
"menu|finance_expense",
"menu|finance_expense_this_month",
"menu|finance_expense_last_month",
"menu|finance_expense_year",
"menu|finance_add_expense",
"menu|finance_expense_categories_future",
"menu|finance_expense_categories|future",
"MENU|FINANCE_EXPENSE_CATEGORIES",
```

- [ ] **Step 3: Pin generated evidence and existing page authority**

Assert the generated Admin ERP contract has the registry-derived count,
`menu\\|finance_expense_categories`, and source-review exclusions for
expense data/write siblings. Re-run existing canonical-admin 401/403/200
coverage for `/admin/finance`; do not add a duplicate route test.

- [ ] **Step 4: Run RED**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'admin_erp or finance'
```

Expected: failure because the parent literal is absent from the private Admin
ERP registry and generated contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1775-1900,11780-11805`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add only `menu|finance_expense_categories` to the private registry**

Add a descriptor with target `/admin/finance`, classification `admin`, feature
key `admin_finance`, authority `SIGNED_CANONICAL_ADMIN_READ`, launch mode
`WEB_NAVIGATION`, and all required source dispositions from the design.

- [ ] **Step 2: Make generated contract wording explicit**

Replace the parent source-review wording with static Categories
read-navigation wording. Keep every finance data, period, write, and variant
callback source-review-required.

- [ ] **Step 3: Run GREEN**

Re-run Task 1's command. Expected: pass; only the lower-case Categories
parent gains `/admin/finance` navigation.

### Task 3: Curate evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`

- [ ] **Step 1: Generate static evidence to a temporary directory**

Run the locked-baseline audit with a new `toanaas-copyfast157-audit-*` root.
Verify the baseline is exact, only the reviewed parent maps to `/admin/finance`
as `NAVIGATION_ONLY`, and all data/write siblings remain source-review-required.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the Categories row/count/text and generated semantic totals. Preserve
unrelated checkout fingerprints, existing finance exclusions, and the Audio
Hub review-pack text.

- [ ] **Step 3: Run focused verification**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main
```

Expected: all pass with no Bot, finance data/write, payment, provider, bridge,
or Railway change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the Categories spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, browser Finance category/expense
form, query parameter, bridge/API route, finance/payment/ledger/webhook code,
or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-finance-expense-categories-navigation-design.md docs/superpowers/plans/2026-07-26-admin-finance-expense-categories-navigation.md
git commit -m "Map finance expense categories to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
