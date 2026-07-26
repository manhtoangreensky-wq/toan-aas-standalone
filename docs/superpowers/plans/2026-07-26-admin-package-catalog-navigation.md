# Admin Package Catalog Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the one read-only Bot Package Catalog help callback an exact fresh Web Admin Packages navigation disposition without widening any package, payment, or admin authority.

**Architecture:** Extend the private, case-sensitive `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` allow-list by one source token. The existing `_map_callback` path will emit a standard canonical-admin `NAVIGATION_ONLY` record; the browser-safe menu catalog and all sensitive sibling callbacks remain untouched.

**Tech Stack:** Python 3.12, static source audit, pytest, FastAPI route inventory.

---

### Task 1: Prove the exact-source boundary with a failing migration test

**Files:**

- Modify: `tests/test_migration_audit.py:1474-1530`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Extend the expected Admin ERP navigation mapping**

Add this row to the `expected` dictionary in
`test_static_audit_keeps_admin_erp_menu_navigation_private_and_exact`:

```python
"menu|admin_packages_catalog": ("/admin/packages", "admin_packages"),
```

Then add the mutation/user sibling values to the existing non-inheritance
loop and assert each has both `target != "/admin/packages"` and
`status != "NAVIGATION_ONLY"`:

```python
"menu|admin_packages_grant_combo",
"menu|admin_packages_grant_monthly",
"menu|admin_packages_user",
"menu|admin_packages_catalog_future",
"MENU|ADMIN_PACKAGES_CATALOG",
```

- [ ] **Step 2: Run the targeted test and confirm the expected RED failure**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k admin_erp_menu_navigation_private_and_exact
```

Expected: failure because `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` does not yet
contain `menu|admin_packages_catalog`.

### Task 2: Add the minimum private catalog entry

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1670-1790`
- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the exact admin read disposition**

Add `menu|admin_packages_catalog` to
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` with this stable contract:

```python
{
    "target": "/admin/packages",
    "classification": "admin",
    "feature_key": "admin_packages",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
}
```

Its source dispositions must include `BOT_ADMIN_ONLY`,
`FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`,
`BOT_PACKAGE_CATALOG_HELP_NOT_REPLAYED`,
`NO_PACKAGE_GRANT_REVOKE_ADJUST_OR_ENTITLEMENT_ACTION`,
`NO_PACKAGE_USER_ID_OR_CODE_TRANSFER`,
`NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`, and `NO_RUNTIME_CLAIM`.
The evidence string must state that frozen Bot source renders static catalog
guidance only and must not claim a package adapter or mutation.

- [ ] **Step 2: Document the ninth exact private admin navigation row**

Update `_render_docs` in `scripts/migration/audit_bot_to_web.py` so the
generated `ADMIN_ERP_MENU_CALLBACK_CONTRACT.md` and generated migration
`README.md` derive their count from the private registry, describe the
catalog-help source, and retain the exclusion of the three sibling
grant/user callbacks. Add assertions in the static-audit fixture that generated
docs contain the ninth row and those exclusions. Do not alter the public menu
catalog documentation.

- [ ] **Step 3: Run the targeted test and confirm GREEN**

Run the Task 1 command again.

Expected: pass; the exact token yields `NAVIGATION_ONLY` with the package
no-transfer dispositions, while the negative tokens still have neither the
Admin Packages target nor navigation-only status.

### Task 3: Regenerate static evidence and run focused verification

**Files:**

- Modify: `reports/migration/*.json` only if generated content changes
- Modify: `docs/migration/*.md` only if generated content changes
- Test: `tests/test_migration_audit.py`, `tests/test_copyfast_auth_api.py`

- [ ] **Step 1: Regenerate the static-only audit from the frozen Bot snapshot**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: the audit is static only, records the frozen Bot baseline, and does
not import/run Bot, providers, PayOS, Telegram, or Web app runtime.

- [ ] **Step 2: Verify focused authority boundaries**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py tests/test_copyfast_auth_api.py
```

Expected: pass. The browser-safe catalog must still exclude raw `menu|` values
and `/admin/packages`; no public Admin package control is added.

- [ ] **Step 3: Check syntax and patch hygiene**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main...HEAD
git diff --check
```

Expected: no syntax or whitespace errors.

### Task 4: Review and commit the isolated slice

**Files:**

- Review: all modified files above

- [ ] **Step 1: Verify scope against the design**

Confirm that no file in the diff edits Bot source, bridge/provider/payment
implementation, browser UI, public menu catalog, or package mutation handler.

- [ ] **Step 2: Commit the completed slice**

Run:

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/superpowers/specs/2026-07-26-admin-package-catalog-navigation-design.md docs/superpowers/plans/2026-07-26-admin-package-catalog-navigation.md reports/migration
git commit -m "Map admin package catalog to Web navigation"
```

Expected: one focused commit with static audit evidence, tests, and no
unrelated source changes.
