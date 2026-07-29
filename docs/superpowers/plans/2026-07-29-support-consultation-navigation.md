# Support Consultation Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map four static Bot consultation-detail callbacks to a fresh signed Web Support Desk entry without transferring Bot state or enabling a support write.

**Architecture:** Extend the audit-only exact allow-list in `scripts/migration/audit_bot_to_web.py`. The existing `/support` page remains Web-owned and independently authenticated; generated migration evidence records only the navigation disposition.

**Tech Stack:** Python 3.12, pytest, static migration auditor, existing FastAPI/Web Support Desk.

---

### Task 1: Add the exact mapping contract test

**Files:**
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Write the failing test**

Add a test named `test_static_audit_maps_only_reviewed_support_consultation_details_to_fresh_web_support` that expects exactly these source/intent pairs:

```python
expected = {
    "support|consult_type|image": "web_support_consultation_image",
    "support|consult_type|document": "web_support_consultation_document",
    "support|consult_type|voice": "web_support_consultation_voice",
    "support|consult_type|package": "web_support_consultation_package",
}
```

For each entry, assert the audit target is `/support`, status is `NAVIGATION_ONLY`, classification is `customer`, the exact intent survives, and `FRESH_SIGNED_WEB_SUPPORT_TICKET_NAVIGATION`, `FINITE_BOT_SUPPORT_TICKET_ENTRY_ONLY`, `BOT_SUPPORT_TICKET_PENDING_OR_RECORD_STATE_NOT_REPLAYED`, `BOT_TICKET_LEAD_ATTACHMENT_ADMIN_OR_TELEGRAM_DELIVERY_NOT_REPLAYED`, `WEB_NATIVE_OWNER_SCOPED_SUPPORT_CASES_ONLY`, `NO_TELEGRAM_TICKET_LEAD_ATTACHMENT_NOTIFICATION_PROVIDER_JOB_WALLET_PAYMENT_REFUND_LEDGER_ACTION`, and `NO_RUNTIME_CLAIM` are present. Assert `video`, `frame_video`, a suffix, case variant, `consult_need`, and `consult_input` remain `SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED` with `NEEDS_FEATURE_DISPOSITION`.

- [ ] **Step 2: Run the focused test to verify RED**

Run:

```powershell
& "C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest -q tests/test_migration_audit.py::test_static_audit_maps_only_reviewed_support_consultation_details_to_fresh_web_support
```

Expected: failure because the exact callback registry has no four reviewed entries yet.

### Task 2: Implement the exact audit-only allow-list

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`

- [ ] **Step 1: Add only the four descriptors**

Extend `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS` with the four exact lower-case callbacks from Task 1. Each descriptor must use `target: "/support"` and the matching opaque `web_support_ticket_intent`. Do not alter `_support_ticket_fresh_web_navigation_mapping`; its existing exact lookup keeps all non-enumerated forms fail-closed.

- [ ] **Step 2: Run the focused test to verify GREEN**

Run the Task 1 command again.

Expected: pass with the expected exact mappings and rejected variants.

### Task 3: Regenerate and verify migration evidence

**Files:**
- Modify (generated, semantic changes only): `docs/migration/SUPPORT_TICKET_CALLBACK_CONTRACT.md`
- Modify (generated, semantic changes only): `reports/migration/parity_gap.json`
- Modify (generated, semantic changes only): `reports/migration/bot_inventory.json`
- Modify (generated, semantic changes only): `reports/migration/web_inventory.json`
- Modify (generated, semantic changes only): other migration documents/reports that the auditor changes for this exact mapping

- [ ] **Step 1: Regenerate static artifacts**

Run the auditor against the frozen source only:

```powershell
& "C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/migration/audit_bot_to_web.py --bot-root "D:\TOANAAS\bot telegram" --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Do not import, execute, compile or modify `bot.py`; inspect `git diff --word-diff` and stage only semantic migration evidence for the four literals.

- [ ] **Step 2: Run focused verification**

Run:

```powershell
& "C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_support_ticket_callbacks_out_of_generic_web_routes tests/test_migration_audit.py::test_static_audit_maps_only_reviewed_support_consultation_details_to_fresh_web_support
& "C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check
```

Expected: both focused tests, syntax check and whitespace check pass; no Bot source or runtime change exists.

- [ ] **Step 3: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration reports/migration docs/superpowers
git commit -m "Map static support consultations to web navigation"
```
