# Admin Finance Export Guidance Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map the static Bot-admin Export Guidance selector to fresh Admin
Finance read navigation without transferring finance data or enabling report
generation, export, file delivery, or a period command.

**Architecture:** Add one exact literal to the private Admin ERP registry.
Reuse the existing signed canonical-admin Finance page and keep all data,
period, export, file, tax, and payment actions source-review-only.

**Tech Stack:** Python 3.12, static source audit, FastAPI route inventory,
pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:155-180,1535-1718`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Move only Export Guidance into the expected private registry**

Add:

```python
"menu|finance_export": ("/admin/finance", "admin_finance"),
```

Remove this exact parent from older source-review assertions, while retaining
the child export callbacks as source-review-only. Keep the existing per-entry
target, authority, status, resolution, and private-metadata assertions.

- [ ] **Step 2: Pin Export Guidance dispositions and siblings**

Assert that the new descriptor contains:

```python
"BOT_FINANCE_EXPORT_GUIDANCE_NOT_REPLAYED",
"NO_CANONICAL_FINANCE_DATA_TRANSFER",
"NO_FINANCE_EXPORT_PERIOD_OR_COMMAND_TRANSFER",
"NO_REPORT_EXPORT_OR_FILE_DELIVERY",
"NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
```

For each callback below, assert exactly
`MENU_SOURCE_REVIEW_REQUIRED`, `NEEDS_FEATURE_DISPOSITION`, and
`menu_callback_requires_finite_exact_web_contract`, with no Admin ERP
metadata:

```python
"menu|finance_export_month",
"menu|finance_export_year",
"menu|finance_export_future",
"menu|finance_export|future",
"MENU|FINANCE_EXPORT",
```

- [ ] **Step 3: Pin generated evidence and existing page authority**

Assert the generated Admin ERP contract has the registry-derived count,
`menu\\|finance_export`, and literal source-review exclusions for both child
callbacks. Re-run the existing canonical-admin page 401/403/200 coverage for
`/admin/finance`; do not add a duplicate route test.

- [ ] **Step 4: Run RED**

Run the focused migration test selection. Expected: failure because the parent
literal is absent from the private registry and generated contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1685-1835,11690-11725`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add only `menu|finance_export` to the private registry**

Use the design document's target, authority, launch mode, no-transfer
dispositions, and source evidence. Do not alter a route, API, bridge, browser
catalog, or finance implementation.

- [ ] **Step 2: Make generated contract wording explicit**

Replace the parent source-review wording with Export Guidance read-navigation
wording. Keep both period-specific export children source-review-required and
preserve Revenue/Expense/Profit, package, and provider boundaries.

- [ ] **Step 3: Run GREEN**

Run the Task 1 command again. Expected: pass; only the lower-case parent
selector gains `/admin/finance` navigation.

### Task 3: Curate evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`

- [ ] **Step 1: Generate static evidence to a temporary directory**

Run the locked-baseline static audit with a new `toanaas-copyfast153-audit-*`
temporary root. Verify the baseline is exact, only the reviewed parent maps to
`/admin/finance` as `NAVIGATION_ONLY`, and child export callbacks remain
source-review-required.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the Export Guidance row/count/text and generated semantic totals.
Preserve unrelated checkout fingerprints, existing Revenue/Expense/Profit
exclusions, and the Audio Hub review-pack text.

- [ ] **Step 3: Run focused verification**

Run the full migration audit tests, focused catalog/admin authorization tests,
`py_compile`, and `git diff --check origin/main`. Expected: all pass with no
Bot change, finance data read, export/file delivery, payment/provider/webhook,
or Railway change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the Export Guidance spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, browser finance form/export-period
parameter, bridge/API route, finance calculation/report/export/file delivery,
payment/ledger/webhook code, or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-finance-export-guidance-navigation-design.md docs/superpowers/plans/2026-07-26-admin-finance-export-guidance-navigation.md
git commit -m "Map finance export guidance to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
