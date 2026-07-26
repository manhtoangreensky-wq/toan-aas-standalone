# Admin Billing PayOS Guidance Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map static Bot-admin PayOS test guidance to fresh Admin Payments read navigation without transferring order/payment data or enabling PayOS test, webhook, wallet, ledger, approval, or rejection behavior.

**Architecture:** Add one exact literal to the private Billing registry. Reuse the existing signed canonical-admin Payments page and keep all case variants, suffixes, and future callbacks source-review-only.

**Tech Stack:** Python 3.12, static source audit, FastAPI route inventory, pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:180-192,1461-1569`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Move only PayOS Guidance into the expected private registry**

Add:

```python
"menu|admin_billing_payos": ("/admin/payments", "admin_payments"),
```

Remove this exact parent from source-review assertions and retain existing per-entry authority, target, status, resolution, and private-metadata checks.

- [ ] **Step 2: Pin PayOS Guidance and all variants**

Assert this descriptor contains:

```python
"BOT_BILLING_PAYOS_TEST_HELP_NOT_REPLAYED",
"NO_ORDER_CODE_OR_PAYMENT_REFERENCE_TRANSFER",
"NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION",
"NO_PAYOS_WALLET_OR_LEDGER_ACTION",
```

For each callback below, assert exactly `MENU_SOURCE_REVIEW_REQUIRED`, `NEEDS_FEATURE_DISPOSITION`, and `menu_callback_requires_finite_exact_web_contract`, with no Billing private metadata:

```python
"menu|admin_billing_payos_future",
"menu|admin_billing_payos|future",
"MENU|ADMIN_BILLING_PAYOS",
```

- [ ] **Step 3: Pin generated evidence and existing page authority**

Assert the generated Billing contract has the registry-derived count and `menu\\|admin_billing_payos`. Re-run existing canonical-admin 401/403/200 coverage for `/admin/payments`; do not add a duplicate route test.

- [ ] **Step 4: Run RED**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k billing
```

Expected: failure because the exact parent is absent from the private Billing registry and generated contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1625-1740,11700-11740`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add only `menu|admin_billing_payos` to the private registry**

Add a descriptor with target `/admin/payments`, classification `admin`, feature key `admin_payments`, authority `SIGNED_CANONICAL_ADMIN_READ`, launch mode `WEB_NAVIGATION`, and these dispositions:

```python
(
    "BOT_ADMIN_ONLY",
    "BOT_BILLING_PAYOS_TEST_HELP_NOT_REPLAYED",
    "FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION",
    "NO_ORDER_CODE_OR_PAYMENT_REFERENCE_TRANSFER",
    "NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION",
    "NO_PAYOS_WALLET_OR_LEDGER_ACTION",
    "NO_RUNTIME_CLAIM",
)
```

Source evidence must state that the Bot page is static manual-command guidance and the Web receives no identity, order/payment reference, ledger/Xu, PayOS/webhook/provider/runtime, or write authority.

- [ ] **Step 2: Make generated contract wording explicit**

Replace the parent source-review wording with PayOS Guidance read-navigation wording. State explicitly that it neither tests PayOS nor touches webhook.

- [ ] **Step 3: Run GREEN**

Re-run Task 1's command. Expected: pass; only the lower-case parent gains `/admin/payments` navigation.

### Task 3: Curate evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`

- [ ] **Step 1: Generate static evidence to a temporary directory**

Run the locked-baseline audit with a new `toanaas-copyfast156-audit-*` root. Verify the baseline is exact, only the parent maps to `/admin/payments` as `NAVIGATION_ONLY`, and variants remain source-review-required.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the PayOS Guidance row/count/text and generated semantic totals. Preserve unrelated checkout fingerprints, finance exclusions, and the Audio Hub review-pack text.

- [ ] **Step 3: Run focused verification**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main
```

Expected: all pass with no Bot, payment/PayOS/webhook, provider, bridge, or Railway change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the PayOS Guidance spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, browser PayOS test button, order code/query parameter, bridge/API route, payment/ledger/webhook code, or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-billing-payos-guidance-navigation-design.md docs/superpowers/plans/2026-07-26-admin-billing-payos-guidance-navigation.md
git commit -m "Map billing PayOS guidance to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
