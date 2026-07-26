# Admin Finance Add-Expense Planning Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the exact Bot finance add-expense help button as a fresh,
independently authorized Web-native Finance Planning entry without replaying
Bot help, command, pending or finance state and without changing any financial
system.

**Architecture:** Add one exact descriptor to a dedicated private Finance
Add-Expense Planning registry, not the canonical Admin ERP read registry. Its
target already has an independently guarded Web-owned planning lifecycle. The
mapping only records a fresh navigation possibility; it cannot carry a raw
callback, Telegram identity/role, Bot help/command/pending state, period,
amount, category, vendor, note, financial record, payment/ledger state or
write intent.

**Tech Stack:** Python 3.12, FastAPI route inventory, static source audit,
pytest.

---

### Task 1: Write the failing dedicated-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:120-190,1585-1860`
- Test: `tests/test_finance_planning_portal_contracts.py`

- [ ] **Step 1: Add the desired private Planning registry expectation**

Add an exact expected descriptor to a dedicated test:

```python
expected = {
    "menu|finance_add_expense": {
        "target": "/admin/finance/planning",
        "classification": "admin",
        "feature_key": "admin_finance_planning",
        "authority": "SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING",
        "launch_mode": "WEB_NAVIGATION",
    },
}
```

Assert the existing `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` stays unchanged
and entirely canonical-read authorized.

- [ ] **Step 2: Pin help and local-planning boundaries**

Assert the descriptor contains exactly these boundary markers in addition to
`BOT_ADMIN_ONLY` and `NO_RUNTIME_CLAIM`:

```python
"FRESH_SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING_NAVIGATION",
"BOT_FINANCE_ADD_EXPENSE_HELP_NOT_REPLAYED",
"BOT_MENU_CALLBACK_CONTEXT_NOT_REPLAYED",
"BOT_PENDING_SESSION_STATE_NOT_REPLAYED",
"NO_BROWSER_NAVIGATION_HISTORY_OR_RESET_ACTION",
"NO_BOT_EXPENSE_COMMAND_OR_FINANCE_EXPENSE_EVENT_TRANSFER",
"NO_CANONICAL_FINANCE_DATA_TRANSFER",
"NO_BOT_EXPENSE_ID_AMOUNT_CATEGORY_VENDOR_NOTE_OR_PRE_ESTABLISHMENT_TRANSFER",
"NO_PAYMENT_PROOF_OR_FINANCIAL_IDENTIFIER_TRANSFER",
"NO_PAYOS_WALLET_XU_LEDGER_PROVIDER_OR_EXPORT_ACTION",
```

Assert the mapping has the dedicated resolution
`reviewed_finance_add_expense_fresh_web_planning_navigation` and only
`finance_add_expense_planning_*` metadata. It must not expose
`admin_erp_*` metadata.

- [ ] **Step 3: Pin fail-closed siblings and generated evidence**

Keep `menu|finance_expense`, period/category child actions, the static
Categories parent’s existing canonical-read disposition, and case/suffix
variants separate. Assert `menu|finance_add_expense_future`,
`menu|finance_add_expense|future` and `MENU|FINANCE_ADD_EXPENSE` are exactly
`MENU_SOURCE_REVIEW_REQUIRED` with no planning metadata.

Assert generated documentation includes
`FINANCE_ADD_EXPENSE_CALLBACK_CONTRACT.md`, the exact lower-case literal,
the local Planning authority and source-review fallback family. Remove only
this parent from prior generic source-review expectations.

- [ ] **Step 4: Run RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'finance_add_expense or admin_erp'
```

Expected: failure because the dedicated private Planning registry and
generated contract do not exist.

### Task 2: Implement the dedicated exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:2100-2200,8420-8510,10690-10715,11775-11860`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the one dedicated literal descriptor**

Create `FINANCE_ADD_EXPENSE_FRESH_WEB_PLANNING_ACTIONS` with only
`menu|finance_add_expense`, target `/admin/finance/planning`, feature key
`admin_finance_planning`, authority
`SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING`, `WEB_NAVIGATION`, and Task 1’s
dispositions.

- [ ] **Step 2: Add a dedicated mapper branch**

Before generic menu handling, look up only the exact identifier and return:

```python
"resolution": "reviewed_finance_add_expense_fresh_web_planning_navigation",
"finance_add_expense_planning_feature_key": "admin_finance_planning",
"finance_add_expense_planning_authority": "SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING",
"finance_add_expense_planning_launch_mode": "WEB_NAVIGATION",
```

Do not alter `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS`, add a public menu
entry, route handler, query parameter, form prefill, bridge method, browser
role control or finance write adapter.

- [ ] **Step 3: Generate the dedicated contract**

Generate `FINANCE_ADD_EXPENSE_CALLBACK_CONTRACT.md` with one exact row and
an explicit statement that the Bot button is help only, no Bot command or
finance event is replayed, and the Web Planning entry is fresh and separately
authorized. Link it from `README.md`. In the Admin ERP prose, replace the
generic source-review claim with a cross-reference that prevents the action
from inheriting the canonical Finance route.

- [ ] **Step 4: Run GREEN**

Re-run Task 1’s command. Expected: pass; only the exact lower-case help
button gets `/admin/finance/planning` with dedicated local-planning metadata.

### Task 3: Regenerate and curate migration evidence

**Files:**

- Create: `docs/migration/FINANCE_ADD_EXPENSE_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`

- [ ] **Step 1: Run static audit in a temporary output directory**

Use the locked Bot baseline and a new `C:\tmp\toanaas-copyfast158-audit-*`
directory. Confirm one exact dedicated row, `NAVIGATION_ONLY`, local-planning
authority, and source-review fallbacks for all finance data/write children and
variants.

- [ ] **Step 2: Curate semantic deltas only**

Copy the regenerated dedicated contract/index and generated parity wording.
Do not copy unrelated checkout fingerprints or stale generated content.

- [ ] **Step 3: Run focused verification**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_finance_planning_portal_contracts.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main
```

Expected: all pass; no Bot, financial system, provider, bridge, payment,
Railway or visible portal UI change.

### Task 4: Review, commit and hand off the isolated slice

**Files:**

- Review: all files above plus the design and plan documents

- [ ] **Step 1: Confirm scope**

Verify `git diff --name-only origin/main` contains no Bot source, public menu
catalog, portal form/UI, bridge, PayOS/webhook/ledger/provider/job, Railway or
deployment file.

- [ ] **Step 2: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/FINANCE_ADD_EXPENSE_CALLBACK_CONTRACT.md docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-finance-add-expense-planning-entry-design.md docs/superpowers/plans/2026-07-26-admin-finance-add-expense-planning-entry.md
git commit -m "Map finance add expense to planning entry"
```

Expected: one focused commit, then push/open PR without a Railway deployment.
