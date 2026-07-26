# Admin Provider Custom Help Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map the parameter-free, Bot-admin Provider Custom Help callback to a fresh canonical Admin Providers read route while retaining provider test/freeze/unfreeze actions behind their existing fail-closed non-browser boundaries.

**Architecture:** Add one exact literal to the private Admin ERP registry. Reuse the current canonical-admin page/API gate and registry-derived Admin ERP evidence; never create browser provider controls or import Bot state.

**Tech Stack:** Python 3.12, FastAPI route inventory, static source audit, pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:1550-1605`
- Modify: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Extend the expected private Admin ERP registry**

Add this literal to `expected` in
`test_static_audit_keeps_admin_erp_menu_navigation_private_and_exact`:

```python
"menu|provider_custom_help": ("/admin/providers", "admin_providers"),
```

Keep the per-entry assertions for target, classification, feature key,
authority, launch mode, `NAVIGATION_ONLY`, exact registry resolution, and
private metadata.

- [ ] **Step 2: Pin the Provider Custom Help boundary**

Add a descriptor assertion for the new literal containing:

```python
"BOT_PROVIDER_CUSTOM_HELP_NOT_REPLAYED",
"NO_PROVIDER_TEST_FREEZE_UNFREEZE_OR_CONTROL_ACTION",
"NO_PROVIDER_NAME_OR_CONFIG_TRANSFER",
"NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
```

For the following callbacks, require the exact source-review fallback:

```python
"menu|admin_provider_test",
"menu|provider_custom_help_future",
"menu|provider_custom_help|future",
"MENU|PROVIDER_CUSTOM_HELP",
```

Each must return `MENU_SOURCE_REVIEW_REQUIRED`,
`NEEDS_FEATURE_DISPOSITION`,
`menu_callback_requires_finite_exact_web_contract`, and no
`admin_erp_feature_key`, `admin_erp_authority`, or
`admin_erp_launch_mode` metadata.

For the existing confirmation callbacks below, require the stricter
`TELEGRAM_ONLY` target/status and `telegram_only` resolution, also with no
Admin ERP metadata:

```python
"menu|admin_confirm_provider_freeze_shopaikey",
"menu|admin_confirm_provider_freeze_video",
"menu|admin_confirm_provider_freeze_image",
"menu|admin_confirm_provider_unfreeze_shopaikey",
```

- [ ] **Step 3: Pin generated evidence and page authority**

In the static-audit fixture test, assert the generated Admin ERP contract uses
the registry-derived count, contains `menu\\|provider_custom_help`, and names
the provider-test source-review exclusion and provider-freeze/unfreeze
Telegram-only exclusions. In
`test_admin_portal_requires_signed_session_and_current_canonical_role`, add
`/admin/providers` to the 401, stale-role 403, and live canonical-admin 200
page loops; update only the expected check count.

- [ ] **Step 4: Run RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'admin_erp_menu_navigation_private_and_exact or static_audit_never_imports_source_and_redacts_secret_literals'
```

Expected: failure because `menu|provider_custom_help` is not yet in the
registry or generated Admin ERP contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1680-1865,10491-10504,11585-11615`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the literal to the private registry**

Add `menu|provider_custom_help` with:

```python
{
    "target": "/admin/providers",
    "classification": "admin",
    "feature_key": "admin_providers",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
}
```

Use the design document’s exact no-transfer dispositions and source evidence.
Do not add an entry to a public capability catalog or any route/API.

- [ ] **Step 2: Make the generated Admin ERP wording explicit**

Keep `admin_erp_menu_action_count` derived from the registry. Update only the
Admin ERP contract text so the Provider Custom Help row is described as a
fresh read navigation, the provider test/config action is source-review-only,
and freeze/unfreeze confirmations are Telegram-only. Preserve the existing
package-child exclusions.

- [ ] **Step 3: Run GREEN**

Run the Task 1 command again. Expected: pass; exactly the lower-case custom
help literal gains the canonical `/admin/providers` navigation.

### Task 3: Curate static evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`
- Test: `tests/test_migration_audit.py`, `tests/test_copyfast_auth_api.py`

- [ ] **Step 1: Generate static evidence to temporary directories**

Run:

```powershell
$tempRoot = Join-Path $env:TEMP ('toanaas-copyfast149-audit-' + [guid]::NewGuid().ToString('N'))
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir (Join-Path $tempRoot 'reports') --docs-dir (Join-Path $tempRoot 'docs')
```

Expected: locked baseline relation `exact`; only the reviewed custom-help
literal maps to `/admin/providers` as `NAVIGATION_ONLY` while the provider
test stays source-review-required and freeze/unfreeze confirmations stay
Telegram-only.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the Provider Custom Help row/count/text and the generated semantic
totals: Admin ERP count `9 → 10`, menu backlog `90 → 89`, typed
source-disposition coverage `72.83% → 72.86%`, and dashboard-navigation
fallbacks `1101 → 1100`. Preserve unrelated Bot-checkout fingerprints and
existing Audio Hub review-pack text.

- [ ] **Step 3: Run focused verification**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main...HEAD
```

Expected: tests and syntax pass; no whitespace error and no Bot/runtime/payment/
provider write change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the Provider Custom Help spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, provider-test/freeze/unfreeze route,
browser form, payment/ledger/webhook code, or Railway configuration appears in
the diff.

- [ ] **Step 2: Commit**

Run:

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py tests/test_copyfast_auth_api.py docs/migration/ADMIN_ERP_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-provider-custom-help-navigation-design.md docs/superpowers/plans/2026-07-26-admin-provider-custom-help-navigation.md
git commit -m "Map provider custom help to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
