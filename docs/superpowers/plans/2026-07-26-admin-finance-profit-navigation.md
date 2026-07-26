# Admin Finance Profit Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map the static Bot-admin Profit selector to fresh Admin Finance read
navigation without transferring finance data or enabling a period/report/export
control.

**Architecture:** Add one exact literal to the private Admin ERP registry.
Reuse the existing signed canonical-admin Finance page and keep all finance
data, periods, reports, exports, tax, and payment actions source-review-only.

**Tech Stack:** Python 3.12, static source audit, FastAPI route inventory,
pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:155-180,1535-1718`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Extend the expected private Admin ERP registry**

Add:

```python
"menu|finance_profit": ("/admin/finance", "admin_finance"),
```

Retain the existing per-entry assertions for exact target, signed canonical
authority, launch mode, status, resolution, and private metadata.

- [ ] **Step 2: Pin Profit dispositions and siblings**

Assert that the new descriptor contains:

```python
"BOT_FINANCE_PROFIT_MENU_NOT_REPLAYED",
"NO_CANONICAL_FINANCE_DATA_TRANSFER",
"NO_FINANCE_PERIOD_OR_PROFIT_PARAMETER_TRANSFER",
"NO_PROFIT_REPORT_OR_FILE_DELIVERY",
"NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
```

For each callback below, assert exactly
`MENU_SOURCE_REVIEW_REQUIRED`, `NEEDS_FEATURE_DISPOSITION`, and
`menu_callback_requires_finite_exact_web_contract`, with no Admin ERP
metadata:

```python
"menu|finance_profit_this_month",
"menu|finance_profit_year",
"menu|finance_profit_future",
"menu|finance_profit|future",
"MENU|FINANCE_PROFIT",
```

- [ ] **Step 3: Pin generated evidence and existing page authority**

In the static-audit fixture test, assert the generated Admin ERP contract has
the registry-derived count, `menu\\|finance_profit`, and literal
source-review exclusions for `menu|finance_profit_this_month` and
`menu|finance_profit_year`. Re-run the existing canonical-admin page
401/403/200 coverage for `/admin/finance`; do not add a duplicate route test.

- [ ] **Step 4: Run RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'admin_erp_menu_navigation_private_and_exact or static_audit_never_imports_source_and_redacts_secret_literals'
```

Expected: failure because the literal is absent from the private registry and
the generated Admin ERP contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1685-1810,11674-11705`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the literal to the private registry**

Add `menu|finance_profit` with the design document's target, authority,
launch mode, no-transfer dispositions, and source evidence. Do not alter a
route, API, bridge, browser catalog, or finance implementation.

- [ ] **Step 2: Make generated Admin ERP wording explicit**

Keep the registry-derived count. Add only the Profit read-navigation wording
plus the source-review exclusions for profit-period/report siblings. Preserve
existing Revenue Month, Expense Month, package, and provider boundaries.

- [ ] **Step 3: Run GREEN**

Run the Task 1 command again. Expected: pass; only the lower-case static
selector gains `/admin/finance` navigation.

### Task 3: Curate evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`
- Test: `tests/test_migration_audit.py`, `tests/test_copyfast_auth_api.py`

- [ ] **Step 1: Generate static evidence to a temporary directory**

Run the locked-baseline static audit with a new `toanaas-copyfast152-audit-*`
temporary root. Verify `baseline_relation` is `exact`, only the reviewed
selector maps to `/admin/finance` as `NAVIGATION_ONLY`, and every profit
period/variant remains source-review-required.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the Profit row/count/text and generated semantic totals. Preserve
unrelated checkout fingerprints, existing Revenue/Expense exclusions, and the
Audio Hub review-pack text.

- [ ] **Step 3: Run focused verification**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main
```

Expected: tests and syntax pass; no whitespace error, Bot change, finance data
read, report/export, payment, provider, webhook, or Railway change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the Profit spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, browser finance form/period/report
parameter, bridge/API route, finance calculation/report/export, payment/ledger
/webhook code, or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

Run:

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-finance-profit-navigation-design.md docs/superpowers/plans/2026-07-26-admin-finance-profit-navigation.md
git commit -m "Map finance profit to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
