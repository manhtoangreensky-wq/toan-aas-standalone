# Admin Billing Approve Guidance Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map static Bot-admin Billing Approval Guidance to fresh Admin Payments
read navigation without transferring payment data or enabling approval,
rejection, PayOS test, webhook, wallet, or ledger behavior.

**Architecture:** Add one exact literal to the private Billing registry. Reuse
the existing signed canonical-admin Payments page and keep adjacent financial
commands, siblings, case variants, suffixes, and future callbacks
source-review-only.

**Tech Stack:** Python 3.12, static source audit, FastAPI route inventory,
pytest.

---

### Task 1: Write the failing exact-boundary tests

**Files:**

- Modify: `tests/test_migration_audit.py:180-193,1461-1534`
- Test: `tests/test_copyfast_auth_api.py:2183-2228`

- [ ] **Step 1: Move only Approval Guidance into the expected private registry**

Add the exact expected entry:

```python
"menu|admin_billing_duyet": ("/admin/payments", "admin_payments"),
```

Remove this exact parent from the older source-review assertions. Retain the
existing per-entry target, authority, status, resolution, and private-metadata
assertions.

- [ ] **Step 2: Pin Approval Guidance dispositions and sensitive siblings**

Assert the new descriptor contains:

```python
"BOT_BILLING_APPROVE_HELP_NOT_REPLAYED",
"NO_BILL_ID_AMOUNT_OR_PAYMENT_REFERENCE_TRANSFER",
"NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION",
"NO_PAYOS_WALLET_OR_LEDGER_ACTION",
```

For each callback below, assert exactly
`MENU_SOURCE_REVIEW_REQUIRED`, `NEEDS_FEATURE_DISPOSITION`, and
`menu_callback_requires_finite_exact_web_contract`, with no Billing private
metadata:

```python
"menu|admin_billing_tuchoi",
"menu|admin_billing_payos",
"menu|admin_billing_duyet_future",
"menu|admin_billing_duyet|future",
"MENU|ADMIN_BILLING_DUYET",
```

- [ ] **Step 3: Pin generated evidence and existing page authority**

Assert the generated Billing contract has the registry-derived count,
`menu\\|admin_billing_duyet`, and literal source-review exclusions for the
two sensitive siblings. Re-run the existing canonical-admin page 401/403/200
coverage for `/admin/payments`; do not add a duplicate route test.

- [ ] **Step 4: Run RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k billing
```

Expected: failure because the parent literal is absent from the private
Billing registry and generated contract.

### Task 2: Implement the private exact navigation disposition

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:1625-1687,11685-11693`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add only `menu|admin_billing_duyet` to the private registry**

Add this exact descriptor inside
`BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS`:

```python
"menu|admin_billing_duyet": {
    "target": "/admin/payments",
    "classification": "admin",
    "feature_key": "admin_payments",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
    "source_dispositions": (
        "BOT_ADMIN_ONLY",
        "BOT_BILLING_APPROVE_HELP_NOT_REPLAYED",
        "FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION",
        "NO_BILL_ID_AMOUNT_OR_PAYMENT_REFERENCE_TRANSFER",
        "NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION",
        "NO_PAYOS_WALLET_OR_LEDGER_ACTION",
        "NO_RUNTIME_CLAIM",
    ),
}
```

Use source evidence that says the Bot page is static manual-command guidance
and the Web receives no identity, payment/bill amount/reference, ledger/Xu,
PayOS/webhook/provider/runtime, or write authority.

- [ ] **Step 2: Make generated contract wording explicit**

Replace the parent source-review wording with Approval Guidance
read-navigation wording. Keep `menu|admin_billing_tuchoi` and
`menu|admin_billing_payos` source-review-required and preserve every existing
Billing boundary.

- [ ] **Step 3: Run GREEN**

Re-run the Task 1 command. Expected: pass; only the lower-case Approval
Guidance parent gains `/admin/payments` navigation.

### Task 3: Curate evidence and verify high-risk boundaries

**Files:**

- Modify: `docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`

- [ ] **Step 1: Generate static evidence to a temporary directory**

Run the locked-baseline audit with a new `toanaas-copyfast154-audit-*`
temporary root. Verify the baseline is exact, only the reviewed parent maps to
`/admin/payments` as `NAVIGATION_ONLY`, and rejection/PayOS sibling callbacks
remain source-review-required.

- [ ] **Step 2: Curate semantic deltas only**

Copy only the Approval Guidance row/count/text and generated semantic totals.
Preserve unrelated checkout fingerprints, finance exclusions, and the Audio
Hub review-pack text.

- [ ] **Step 3: Run focused verification**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_copyfast_auth_api.py -k 'catalog_exposes_a_closed_browser_safe_menu_capability_catalog or admin_portal_requires_signed_session_and_current_canonical_role'
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check origin/main
```

Expected: all pass with no Bot change, payment approval/rejection, manual
top-up, PayOS/webhook, provider, bridge, or Railway change.

### Task 4: Commit and hand off the isolated slice

**Files:**

- Review: all files above plus the Approval Guidance spec and plan files

- [ ] **Step 1: Confirm scope**

Confirm no Bot file, public menu catalog, browser Payments approval form,
bill ID/amount/query parameter, bridge/API route, payment/ledger/webhook code,
or Railway configuration appears in the diff.

- [ ] **Step 2: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/BILLING_MENU_CALLBACK_CONTRACT.md docs/migration/README.md docs/migration/FALLBACK_FEATURE_DISPOSITION.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/superpowers/specs/2026-07-26-admin-billing-approve-guidance-navigation-design.md docs/superpowers/plans/2026-07-26-admin-billing-approve-guidance-navigation.md
git commit -m "Map billing approval guidance to Web navigation"
```

Expected: one focused commit; push and open a PR without deploying Railway.
