# Safe Support & Ticket Entry Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow seven reviewed, exact Telegram support/ticket entry literals to open a fresh signed Web Support Desk or Ticket Center route without transferring Telegram callback data, identity, ticket state, or authorization.

**Architecture:** The static migration auditor receives a closed, case-sensitive allowlist beside the existing Feedback allowlist. A dedicated mapper emits `NAVIGATION_ONLY` only when the literal exactly matches the allowlist and the target Web route is present. Every suffix, case variant, dynamic template, ticket identifier, attachment, reply, admin, refund, lead, payment, provider, job, and Bot-pending-state path remains in the existing fail-closed `SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED` boundary.

**Tech Stack:** Python 3.11+ static AST auditor, checked-in migration Markdown/JSON evidence, pytest.

---

## Scope and non-goals

- No `bot.py`, Bot branch, bridge, PayOS, wallet/Xu, provider, webhook, or Telegram runtime change.
- No change to Video Studio, capability/skill/video/QA files owned by `P1.LocalVideoStudio26`.
- No browser route, query parameter, form field, API request, storage entry, or database record receives a raw Bot callback, ticket/lead/attachment ID, category, pending input, or Telegram identity.
- `/support` and `/tickets` remain existing signed Web-native routes. This work only records a reviewed fresh-entry disposition in the static audit; it does not assert a Bot workflow-equivalence or runtime success.

## File structure

- Modify: `scripts/migration/audit_bot_to_web.py`
  - Adds a closed `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS` registry and exact mapper.
  - Updates generated Support/Ticket contract wording and rows.
- Modify: `tests/test_migration_audit.py`
  - Proves the exact seven literals are navigation-only and all unsafe variants remain fail-closed.
  - Proves generated contract output contains the finite exception and retains the boundary text.
- Regenerate: `docs/migration/*.md`, `reports/migration/*.json`
  - Generated only by the static auditor against frozen Bot SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
- Create: `docs/superpowers/plans/2026-07-29-support-ticket-entry-parity.md`
  - This implementation plan.

### Task 1: Add the regression test first

**Files:**

- Modify: `tests/test_migration_audit.py:3228-3400`

- [ ] **Step 1: Add the exact finite-entry expectations to `test_static_audit_keeps_support_ticket_callbacks_out_of_generic_web_routes`.**

  Insert this block before the existing `customer_identifiers` tuple, keeping the raw input case-sensitive:

  ```python
  support_ticket_navigation = {
      "support|start": ("/support", "web_support_start"),
      "support|consult": ("/support", "web_support_consultation"),
      "support|premium": ("/support", "web_support_premium_consultation"),
      "support|admin_contact": ("/support", "web_support_admin_contact"),
      "ticket|start": ("/support", "web_support_ticket_start"),
      "support|ticket": ("/support", "web_support_ticket_create"),
      "ticket|mine": ("/tickets", "web_ticket_history"),
  }
  expected_navigation_dispositions = {
      "FRESH_SIGNED_WEB_SUPPORT_TICKET_NAVIGATION",
      "FINITE_BOT_SUPPORT_TICKET_ENTRY_ONLY",
      "NO_RAW_BOT_CALLBACK_OR_TICKET_TO_BROWSER",
      "BOT_SUPPORT_TICKET_PENDING_OR_RECORD_STATE_NOT_REPLAYED",
      "BOT_TICKET_LEAD_ATTACHMENT_ADMIN_OR_TELEGRAM_DELIVERY_NOT_REPLAYED",
      "WEB_NATIVE_OWNER_SCOPED_SUPPORT_CASES_ONLY",
      "NO_TELEGRAM_TICKET_LEAD_ATTACHMENT_NOTIFICATION_PROVIDER_JOB_WALLET_PAYMENT_REFUND_LEDGER_ACTION",
      "NO_RUNTIME_CLAIM",
  }
  assert set(audit.SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS) == set(support_ticket_navigation)
  for identifier, (target, web_intent) in support_ticket_navigation.items():
      mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
      assert mapped["target"] == target
      assert mapped["classification"] == "customer"
      assert mapped["status"] == "NAVIGATION_ONLY"
      assert mapped["resolution"] == "reviewed_support_ticket_fresh_web_navigation"
      assert mapped["support_ticket_navigation_authority"] == "SIGNED_WEB_NATIVE_CUSTOMER"
      assert mapped["support_ticket_navigation_launch_mode"] == "WEB_NAVIGATION"
      assert mapped["web_support_ticket_intent"] == web_intent
      assert set(mapped["source_dispositions"]) == expected_navigation_dispositions
  ```

- [ ] **Step 2: Move the seven exact literals out of the existing generic-customer negative set and add unsafe near-miss tests.**

  Keep the existing unsafe examples and append this explicit case/suffix/dynamic check:

  ```python
  for identifier in (
      "SUPPORT|START",
      "support|start|future",
      "support|consult|video",
      "support|premium|business",
      "support|admin_contact|future",
      "ticket|start|future",
      "support|ticket|42",
      "ticket|mine|future",
  ):
      mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
      assert mapped["target"] == "SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED"
      assert mapped["classification"] == "customer"
      assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
      assert mapped["resolution"] == "support_ticket_callback_requires_web_native_owner_role_contract"
      assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]
  ```

  Add these templates to the existing template loop so dynamic sources cannot inherit the finite route:

  ```python
  ("support|consult|{*}", "customer"),
  ("support|ticket|{*}", "customer"),
  ("ticket|mine|{*}", "customer"),
  ```

- [ ] **Step 3: Extend the synthetic `run_audit` fixture in the same test.**

  Add finite values and unsafe formatted values to its generated `bot.py`, then assert the finite values are recorded as `NAVIGATION_ONLY`, dynamic values remain source-review-required, and the generated Support/Ticket contract names `reviewed_support_ticket_fresh_web_navigation`.

- [ ] **Step 4: Run the focused test and verify it fails because the registry does not yet exist.**

  Run:

  ```powershell
  & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_support_ticket_callbacks_out_of_generic_web_routes
  ```

  Expected: a failure mentioning missing `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS` or the current `SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED` result for an exact allowlisted literal.

### Task 2: Implement the closed registry and exact mapper

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:7000-7180`

- [ ] **Step 1: Add the finite registry directly after `FEEDBACK_FRESH_WEB_SUPPORT_NAVIGATION_ACTIONS`.**

  ```python
  SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, str]] = {
      "support|start": {"target": "/support", "web_support_ticket_intent": "web_support_start"},
      "support|consult": {"target": "/support", "web_support_ticket_intent": "web_support_consultation"},
      "support|premium": {"target": "/support", "web_support_ticket_intent": "web_support_premium_consultation"},
      "support|admin_contact": {"target": "/support", "web_support_ticket_intent": "web_support_admin_contact"},
      "ticket|start": {"target": "/support", "web_support_ticket_intent": "web_support_ticket_start"},
      "support|ticket": {"target": "/support", "web_support_ticket_intent": "web_support_ticket_create"},
      "ticket|mine": {"target": "/tickets", "web_support_ticket_intent": "web_ticket_history"},
  }
  ```

- [ ] **Step 2: Add `_support_ticket_fresh_web_navigation_mapping` and call it before the generic source-review mapping.**

  The helper must use `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS.get(identifier)`, never lower/casefold the registry key, and return this exact boundary shape:

  ```python
  {
      "source_kind": source_kind,
      "source": identifier,
      "target": target,
      "classification": "customer",
      "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
      "resolution": "reviewed_support_ticket_fresh_web_navigation",
      "source_dispositions": (
          "FRESH_SIGNED_WEB_SUPPORT_TICKET_NAVIGATION",
          "FINITE_BOT_SUPPORT_TICKET_ENTRY_ONLY",
          "NO_RAW_BOT_CALLBACK_OR_TICKET_TO_BROWSER",
          "BOT_SUPPORT_TICKET_PENDING_OR_RECORD_STATE_NOT_REPLAYED",
          "BOT_TICKET_LEAD_ATTACHMENT_ADMIN_OR_TELEGRAM_DELIVERY_NOT_REPLAYED",
          "WEB_NATIVE_OWNER_SCOPED_SUPPORT_CASES_ONLY",
          "NO_TELEGRAM_TICKET_LEAD_ATTACHMENT_NOTIFICATION_PROVIDER_JOB_WALLET_PAYMENT_REFUND_LEDGER_ACTION",
          "NO_RUNTIME_CLAIM",
      ),
      "support_ticket_navigation_authority": "SIGNED_WEB_NATIVE_CUSTOMER",
      "support_ticket_navigation_launch_mode": "WEB_NAVIGATION",
      "web_support_ticket_intent": str(action["web_support_ticket_intent"]),
      "evidence": evidence,
  }
  ```

  Call it in `_map_support_ticket_callback` after the Feedback mapper and before `token.startswith(...)`. A no-match must return `None`, leaving all old source-review behavior untouched.

- [ ] **Step 3: Run the focused test and verify it passes.**

  Run the same command from Task 1, Step 4.

  Expected: `1 passed`.

### Task 3: Render truthful migration evidence

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:11389-11430, 11900-11916`
- Regenerate: `docs/migration/SUPPORT_TICKET_CALLBACK_CONTRACT.md`
- Regenerate: `docs/migration/README.md`
- Regenerate: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Regenerate: `docs/migration/FALLBACK_FEATURE_DISPOSITION.md`
- Regenerate: `reports/migration/preflight.json`
- Regenerate: `reports/migration/bot_inventory.json`
- Regenerate: `reports/migration/web_inventory.json`
- Regenerate: `reports/migration/parity_gap.json`

- [ ] **Step 1: Add generated contract rows for the seven finite literals.**

  Build a `support_ticket_fresh_navigation_contract_rows` list from `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS`, then prepend its rows to `support_ticket_contract_rows`. Each row must use the exact target, resolution `reviewed_support_ticket_fresh_web_navigation`, and state that it opens only a fresh signed Web route with no callback, ticket/lead/attachment ID, pending state, Bot admin authority, Telegram delivery, provider/job/payment/wallet/refund/ledger action, or runtime claim.

- [ ] **Step 2: Correct the generated explanatory text.**

  Replace the claim that nine Feedback literals are the sole exception with wording that distinguishes:

  ```text
  Seven exact Support/Ticket entry literals and nine exact Feedback literals are the finite navigation-only exceptions.
  ```

  State that the new seven values do not preselect a Web category, fetch a Bot ticket, or create a case. Keep the existing explanation that every unlisted source remains source-review-required and cannot inherit `/support`, `/tickets`, or an Admin route.

- [ ] **Step 3: Regenerate artifacts from the frozen static Bot snapshot.**

  Run this exact static-only command from the Web worktree. It reads the Bot repository, materializes SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4` in an audit-owned temporary snapshot, and never imports or modifies Bot code:

  ```powershell
  & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py `
    --bot-root 'C:\Users\toann\Documents\Codex\2026-05-31\files-mentioned-by-the-user-bot\toanaas-hotfix-28ff87f' `
    --web-root . `
    --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 `
    --report-dir reports/migration `
    --docs-dir docs/migration
  ```

  Expected: JSON with `"ok": true`, source baseline SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`, and no secret-shaped literal in generated outputs.

- [ ] **Step 4: Run focused regression tests for the auditor and existing Web-native Support Desk.**

  ```powershell
  & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q `
    tests/test_migration_audit.py::test_static_audit_keeps_support_ticket_callbacks_out_of_generic_web_routes `
    tests/test_copyfast_support.py `
    tests/test_support_portal_contracts.py `
    tests/test_support_recovery_read_model_contracts.py
  ```

  Expected: all selected tests pass; no Bot, payment, provider, or runtime integration is contacted.

### Task 4: Verify, review, and integrate the isolated PR

**Files:**

- Verify: `scripts/migration/audit_bot_to_web.py`, `tests/test_migration_audit.py`, regenerated migration evidence

- [ ] **Step 1: Run static safety checks.**

  ```powershell
  & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall -q .
  node --check static/portal/portal.js
  node --check static/portal/integration.js
  node --check static/portal/service-worker.js
  git diff --check
  ```

  Expected: every command exits `0`.

- [ ] **Step 2: Inspect the diff against `origin/main`.**

  ```powershell
  git diff --check origin/main...HEAD
  git diff --name-only origin/main...HEAD
  ```

  Expected: only the plan, static auditor, focused migration test, and generated migration evidence are present; no Bot, Video Studio, PayOS/wallet/provider/webhook, capability/skill, or LocalVideoStudio26-owned file is changed.

- [ ] **Step 3: Request two-stage review.**

  First dispatch a spec reviewer to verify every allowlisted literal, route, fail-closed negative case, and non-goal. Then dispatch a code-quality/security reviewer to inspect exact-match behavior, case sensitivity, generated output, and absence of browser/state transfer. Resolve all important findings before proceeding.

- [ ] **Step 4: Commit and push the independently reviewable PR branch.**

  ```powershell
  git add docs/superpowers/plans/2026-07-29-support-ticket-entry-parity.md scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration reports/migration
  git commit -m "Add safe support and ticket entry parity"
  git push -u origin feature/p0-webapp-copyfast161-support-ticket-entry-parity
  ```

  Then create a PR to `main` titled `Add safe support and ticket entry parity`, wait for the Web App quality gate, and merge only after it is green.

## Plan self-review

- Scope is limited to a finite static-audit navigation contract and the existing Web-owned Support Desk; it does not add a provider, payment, Bot, bridge, or video capability.
- Every exact literal is listed, every requested target is explicit, and unsafe values have an explicit negative test.
- The static audit command uses the frozen Bot SHA and an audit-owned source snapshot rather than the mutable Bot worktree.
- Test-first, red/green, generated-artifact verification, diff checks, two-stage review, and separate PR/merge gates are included.
