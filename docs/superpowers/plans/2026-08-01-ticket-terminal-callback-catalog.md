# Ticket Terminal Callback Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify only proven finite Bot Ticket menu/list/search/category controls as exact, fail-closed `TELEGRAM_ONLY` audit records without changing Web Support Desk runtime behavior.

**Architecture:** `audit_bot_to_web.py` gains raw finite customer/admin Ticket catalogs and a terminal envelope helper.  The Support/Ticket mapper checks exact raw membership before its generic source-review boundary, while using a trimmed normalized token only to keep whitespace variants inside the same fail-closed boundary.  Generated reports remove only finite Ticket terminal records from the backlog.

**Tech Stack:** Python static AST audit, pytest, generated JSON/Markdown migration evidence.

---

### Task 1: Write the red Ticket catalog contract

**Files:**

- Modify: `tests/test_migration_audit.py` near the Support/Ticket static audit
  test and current frozen-evidence test.

- [ ] **Step 1: Assert the exact two finite raw catalogs.**

```python
assert set(audit.TICKET_CUSTOMER_TELEGRAM_ONLY_ACTIONS) == {
    "ticket|cat|payment_topup", "ticket|cat|image_error",
    "ticket|cat|video_error", "ticket|cat|document_pdf",
    "ticket|cat|package_combo", "ticket|cat|refund",
    "ticket|cat|feature_request", "ticket|cat|other",
    "ticket|cat|lead_consulting",
}
assert set(audit.TICKET_ADMIN_TELEGRAM_ONLY_ACTIONS) == {
    "ticket|admin", "ticket|al|new|0", "ticket|al|high|0",
    "ticket|al|refund|0", "ticket|asearch|all", "ticket|asearch|user",
    "ticket|stats", "ticket|templates",
}
```

- [ ] **Step 2: Assert terminal envelopes and classifications.**

```python
customer = audit._map_callback("ticket|cat|refund", "callback_data", evidence, routes)
assert customer["target"] == customer["status"] == "TELEGRAM_ONLY"
assert customer["classification"] == "customer"
assert "BOT_SUPPORT_TICKET_PENDING_OR_RECORD_STATE" in customer["source_dispositions"]

admin = audit._map_callback("ticket|stats", "callback_data", evidence, routes)
assert admin["target"] == admin["status"] == "TELEGRAM_ONLY"
assert admin["classification"] == "admin"
assert "BOT_ADMIN_ONLY" in admin["source_dispositions"]
```

- [ ] **Step 3: Assert raw exactness and residual boundary.**

```python
for source in (
    "TICKET|CAT|REFUND", " ticket|stats", "ticket|stats ",
    "ticket|cat|unknown", "ticket|al|new|1", "ticket|pv|12",
    "ticket|reply|12", "ticket|st|12|resolved", "ticket|send|12",
):
    mapped = audit._map_callback(source, "callback_data", evidence, routes)
    assert mapped["target"] == "SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED"
    assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
```

- [ ] **Step 4: Run red test.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k support_ticket
```

Expected: failure because the finite terminal catalogs and envelopes do not
exist.

### Task 2: Implement finite Ticket terminal mapping

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py` near the Support/Ticket
  registries and `_map_support_ticket_callback`.

- [ ] **Step 1: Add raw terminal catalogs.**

```python
TICKET_CUSTOMER_TELEGRAM_ONLY_ACTIONS = frozenset({...})
TICKET_ADMIN_TELEGRAM_ONLY_ACTIONS = frozenset({...})
```

- [ ] **Step 2: Add terminal mapping helper.**

The helper returns an audit-only envelope with `target` and `status` equal to
`TELEGRAM_ONLY`, a correct customer/admin classification, pending/record or
admin mutation dispositions, `NO_WEB_NAVIGATION_OR_BROWSER_ACTION`,
`NO_TICKET_LEAD_ATTACHMENT_OR_TELEGRAM_STATE_REPLAY`,
`NO_WALLET_PAYMENT_REFUND_OR_LEDGER_ACTION`, and `NO_RUNTIME_CLAIM`.

- [ ] **Step 3: Preserve exact raw lookup and fail-closed whitespace.**

Use raw membership for fresh-navigation and terminal catalogs.  Use
`raw_identifier.strip().casefold()` only to recognize a `support|`, `ticket|`
or `feedback|` namespace before returning the current source-review mapping.
Do not alter reviewed fresh Web navigation entries.

- [ ] **Step 4: Run the Task 1 command green.**

Expected: pass.

### Task 3: Regenerate evidence and documentation

**Files:**

- Modify: `docs/migration/SUPPORT_TICKET_CALLBACK_CONTRACT.md` through the
  generator.
- Regenerate: `docs/migration/*.md` and `reports/migration/*.json` from the
  frozen Bot baseline.
- Modify: `docs/migration/TEST_EVIDENCE.md` if the current metric changes.

- [ ] **Step 1: Add exact terminal rows to the Support/Ticket contract.**

Show customer categories and Bot-admin menu/list/search literals as
`TELEGRAM_ONLY`; keep dynamic IDs and all residual values source-review.

- [ ] **Step 2: Regenerate static-only evidence.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: source text/AST/Git metadata only; no Bot import/start or live
request.

### Task 4: Verify, review and integrate

**Files:**

- Verify: audit script, migration test, migration evidence, Support Ticket
  contract and existing Web Support Desk regression.

- [ ] **Step 1: Run targeted verification.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py tests/test_copyfast_support.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check
```

- [ ] **Step 2: Review scope and commit.**

Confirm the diff contains only audit/test/docs/evidence/spec files.  Do not
alter Bot/runtime/provider/payment/job/Video files.  Commit, push, open a PR,
merge only after CI passes, then perform bounded Railway deployment and public
health/route-boundary smoke checks.

## Plan self-review

- All 17 exact sources are named; no dynamic ticket ID action is promoted.
- Case/whitespace/suffix/unknown actions remain source-review-required.
- Existing fresh navigation stays unchanged.
- The task has no runtime or external-effect claim.
