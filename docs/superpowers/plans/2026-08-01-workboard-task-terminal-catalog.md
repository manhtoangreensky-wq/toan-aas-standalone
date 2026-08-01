# Workboard Task Terminal Callback Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify only the proven frozen-Bot production pipeline/task controls as exact, fail-closed `TELEGRAM_ONLY` audit records without changing Web Workboard runtime behavior.

**Architecture:** `audit_bot_to_web.py` gets finite raw template registries plus a terminal envelope.  The mapper checks exact lower-case values before its generic `pipe|*`/`task|*` source-review boundary.  Generated migration evidence records finite terminal controls while case/suffix/future values remain visible in the backlog.

**Tech Stack:** Python static AST audit, pytest, generated JSON/Markdown migration evidence.

---

### Task 1: Write the red terminal-catalog contract

**Files:**

- Modify: `tests/test_migration_audit.py` in
  `test_static_audit_keeps_workboard_task_callbacks_out_of_generic_web_routes`.
- Modify: `tests/test_migration_audit.py` in the current migration-evidence
  assertions.

- [ ] **Step 1: Define the finite source templates in the test.**

```python
expected_terminal_templates = {
    "pipe|stage|voice|{*}", "pipe|stage|edit|{*}",
    "pipe|stage|review|{*}", "pipe|stage|publish|{*}",
    "pipe|stage|script|{*}", "pipe|status|ready|{*}",
    "pipe|status|published|{*}", "pipe|status|blocked|{*}",
    "task|status|ready|{*}", "task|status|blocked|{*}",
    "task|handoff|x|{*}",
}
assert set(audit.WORKBOARD_TASK_TELEGRAM_ONLY_TEMPLATES) == expected_terminal_templates
```

- [ ] **Step 2: Assert the terminal mapping envelope.**

```python
mapped = audit._map_callback("pipe|stage|review|12", "callback_data", evidence, routes)
assert mapped["target"] == "TELEGRAM_ONLY"
assert mapped["status"] == "TELEGRAM_ONLY"
assert mapped["classification"] == "admin"
assert mapped["resolution"] == "workboard_task_requires_telegram_admin_context"
assert "BOT_ADMIN_ONLY" in mapped["source_dispositions"]
assert "CANONICAL_BOT_PRODUCTION_WORKFLOW_STATE" in mapped["source_dispositions"]
assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
```

- [ ] **Step 3: Assert exactness and source-review drift.**

```python
for source in (
    "PIPE|STAGE|REVIEW|12", "pipe|stage|review|12|future",
    "pipe|stage|unknown|12", "task|status|working|31",
    "task|handoff|y|31", "task|future|opaque",
):
    mapped = audit._map_callback(source, "callback_data", evidence, routes)
    assert mapped["target"] == "WORKBOARD_TASK_SOURCE_REVIEW_REQUIRED"
    assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
```

- [ ] **Step 4: Run the focused test to prove it fails.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k workboard_task
```

Expected: failure because the finite terminal catalog does not yet exist.

### Task 2: Implement the finite terminal mapper

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py` near
  `WORKBOARD_TASK_CALLBACK_PREFIXES` and `_map_workboard_task_callback`.

- [ ] **Step 1: Add the raw finite template catalog.**

```python
WORKBOARD_TASK_TELEGRAM_ONLY_TEMPLATES = frozenset({
    "pipe|stage|voice|{*}", "pipe|stage|edit|{*}",
    "pipe|stage|review|{*}", "pipe|stage|publish|{*}",
    "pipe|stage|script|{*}", "pipe|status|ready|{*}",
    "pipe|status|published|{*}", "pipe|status|blocked|{*}",
    "task|status|ready|{*}", "task|status|blocked|{*}",
    "task|handoff|x|{*}",
})
```

- [ ] **Step 2: Add a Telegram-only mapping helper.**

```python
def _workboard_task_telegram_only_mapping(identifier, source_kind, evidence):
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "TELEGRAM_ONLY",
        "classification": "admin",
        "status": "TELEGRAM_ONLY",
        "resolution": "workboard_task_requires_telegram_admin_context",
        "source_dispositions": (
            "TELEGRAM_IDENTITY_CONTEXT", "BOT_ADMIN_ONLY",
            "BOT_PRODUCTION_JOB_OR_TASK_IDENTIFIER",
            "CANONICAL_BOT_PRODUCTION_WORKFLOW_STATE",
            "NO_PRODUCTION_JOB_TASK_OR_HANDOFF_STATE_REPLAY",
            "NO_PROVIDER_JOB_OUTPUT_OR_DELIVERY_ACTION", "NO_RUNTIME_CLAIM",
        ),
        "evidence": evidence,
    }
```

- [ ] **Step 3: Match only finite raw callback/template shapes.**

Convert a concrete callback's ASCII-decimal last segment to `{*}` only after
confirming that the raw source begins with a lower-case supported family and
has the expected segment count.  Template mapping uses exact membership.
Every non-member, including leading/trailing whitespace or a Unicode digit,
reaches the existing generic source-review mapping.

- [ ] **Step 4: Run the focused test green.**

Run the Task 1 command. Expected: pass.

### Task 3: Regenerate migration evidence and contract

**Files:**

- Modify: `docs/migration/WORKBOARD_TASK_CALLBACK_CONTRACT.md`.
- Regenerate: `docs/migration/*.md` and `reports/migration/*.json` from the
  frozen Bot baseline.
- Modify: `docs/migration/TEST_EVIDENCE.md` only if its current metric changes.

- [ ] **Step 1: Update the Workboard/Task boundary table.**

List the exact finite templates as `TELEGRAM_ONLY`; state that raw exactness is
required and all other values remain source-review-required.

- [ ] **Step 2: Regenerate static-only evidence.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: no Bot import/start and no live external request.

### Task 4: Verify, review and integrate

**Files:**

- Verify: audit script, migration test, migration evidence and contract.

- [ ] **Step 1: Run targeted verification.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check
```

- [ ] **Step 2: Review scope and commit.**

Confirm that the branch touches only audit/test/docs/evidence files and does
not alter Bot, Web Workboard runtime, provider/payment/job code or coordinated
Video/Motion files.  Then commit, push, create a PR, merge only after CI is
green, and perform the bounded Railway health check.

## Plan self-review

- Every promoted literal is explicitly named and derived from the frozen
  handler/button evidence.
- Case, whitespace, suffix, unknown action and future values remain
  source-review-required.
- No raw Bot callback becomes a Web route or browser protocol.
- The task has no runtime or external-effect claim.
