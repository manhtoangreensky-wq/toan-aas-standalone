# Admin Billing Pending Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map the parameter-free Pending Bills Bot help callback to a fresh signed Admin Payments read route without turning adjacent billing commands into Web payment actions.

**Architecture:** Extend the private exact billing navigation registry by one literal. Reuse the existing canonical-admin read path; derive generated Billing contract text from the registry and preserve every sibling as source-review-only.

**Tech Stack:** Python 3.12, static source audit, pytest, FastAPI route inventory.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:1423-1472`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Extend the expected billing registry**

Replace the one-item registry assertion with:

```python
expected = {
    "menu|billing": ("/admin/payments", "admin_payments"),
    "menu|admin_billing_pending": ("/admin/payments", "admin_payments"),
}
assert set(audit.BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == set(expected)
```

For each expected item, assert `SIGNED_CANONICAL_ADMIN_READ`,
`WEB_NAVIGATION`, `NAVIGATION_ONLY`, and
`reviewed_billing_menu_admin_navigation`.

- [ ] **Step 2: Add the negative action boundary**

For each callback below, assert `target != "/admin/payments"` and
`status != "NAVIGATION_ONLY"`:

```python
"menu|admin_billing_duyet",
"menu|admin_billing_tuchoi",
"menu|admin_billing_payos",
"menu|admin_billing_pending_future",
"MENU|ADMIN_BILLING_PENDING",
```

Pin the pending descriptor dispositions:

```python
"BOT_BILLING_PENDING_HELP_NOT_REPLAYED",
"NO_BILL_ID_OR_PAYMENT_REFERENCE_TRANSFER",
"NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION",
"NO_PAYOS_WALLET_OR_LEDGER_ACTION",
```

- [ ] **Step 3: Assert generated documentation**

In `test_static_audit_never_imports_source_and_redacts_secret_literals`, load
`BILLING_MENU_CALLBACK_CONTRACT.md` from temporary generated docs and assert
the registry-derived count, `menu\\|admin_billing_pending`, and the literal
approve/reject/PayOS-test sibling exclusions. Also assert the generated README
uses the private-registry-derived Billing count.

- [ ] **Step 4: Run RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'billing_menu_private_canonical_admin_navigation_only or static_audit_never_imports_source_and_redacts_secret_literals'
```

Expected: failure because the registry and generated contract lack
`menu|admin_billing_pending`.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1632-1665,10420-10470,11490-11550`
- Test: `tests/test_migration_audit.py`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Add the literal to the billing registry**

Add `menu|admin_billing_pending` with:

```python
{
    "target": "/admin/payments",
    "classification": "admin",
    "feature_key": "admin_payments",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
}
```

Its dispositions include the four Task 1 strings, `BOT_ADMIN_ONLY`, and
`NO_RUNTIME_CLAIM`. Its evidence states the Bot action is parameter-free Pending
Bills guidance and a fresh Web route imports no Bot state.

- [ ] **Step 2: Make generated Billing docs registry-derived**

Create `billing_menu_action_count = len(billing_menu_contract_rows)` in
`_render_docs`. Use it in the Billing contract heading; render the pending row;
replace “sole reviewed disposition” with language covering the two read
navigations; and explicitly preserve approve/reject/PayOS-test source review.

- [ ] **Step 3: Run GREEN**

Run the Task 1 command again.

Expected: pass; only the exact pending literal gains canonical Admin Payments
read navigation.

- [ ] **Step 4: Pin the mapped page authority**

Add `/admin/payments` to the existing Admin portal canonical-role test for
unauthenticated (401), stale cached Admin (403), and live canonical Admin
(200) cases. Keep the target page route read-only; do not add a browser
callback or payment control.

### Task 3: Verify semantic generated evidence and focused boundaries

**Files:**

- Modify: `docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`
- Test: `tests/test_migration_audit.py`, `tests/test_copyfast_auth_api.py`

- [ ] **Step 1: Generate static evidence to temporary directories**

Run:

```powershell
$tempRoot = Join-Path $env:TEMP 'toanaas-copyfast148-audit'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir (Join-Path $tempRoot 'reports') --docs-dir (Join-Path $tempRoot 'docs')
```

Expected: static-only output contains the exact pending mapping and does not
overwrite unrelated tracked audit snapshots.

- [ ] **Step 2: Curate semantic doc deltas only**

Update the five listed docs only for the pending mapping, menu backlog decrement,
coverage value, and known-gap decrement. Preserve unrelated fingerprints,
source-line drift observations, and document links.

- [ ] **Step 3: Run focused verification**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main...HEAD
```

Expected: selected tests and syntax check pass with no whitespace error.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the billing Pending spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, payment/provider/bridge write route,
browser form, webhook, or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

Run:

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py tests/test_copyfast_auth_api.py docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-billing-pending-navigation-design.md docs/superpowers/plans/2026-07-26-admin-billing-pending-navigation.md
git commit -m "Map admin billing pending to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
