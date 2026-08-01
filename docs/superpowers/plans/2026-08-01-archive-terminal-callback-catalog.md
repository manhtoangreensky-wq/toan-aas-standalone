# Archive Terminal Callback Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify four frozen Bot Archive pending-state callbacks as exact, fail-closed `TELEGRAM_ONLY` audit records without changing the independent Web Archive runtime.

**Architecture:** `audit_bot_to_web.py` gains a finite raw callback catalog and a terminal-envelope helper. The Archive mapper uses the raw source for every registry lookup, retaining normalization only for namespace recognition and forwarding every non-exact/case-variant value to the source-review boundary. Generated migration evidence records nine frozen occurrences as terminal while two dynamic department-template occurrences remain visible.

**Tech Stack:** Python static AST audit, pytest, generated JSON/Markdown migration evidence.

---

### Task 1: Write the red Archive catalog contract

**Files:**
- Modify: `tests/test_migration_audit.py` in `test_static_audit_maps_only_reviewed_archive_literals_to_fresh_admin_navigation`.
- Modify: `tests/test_migration_audit.py` in `test_current_migration_evidence_records_frozen_baseline_and_historical_bridge`.

- [ ] **Step 1: Assert the exact terminal catalog.**

```python
expected_terminal = {
    "archive|back_department",
    "archive|change_dept",
    "archive|discard_to_dept",
    "archive|edit",
}
assert set(audit.ARCHIVE_PENDING_STATE_TELEGRAM_ONLY_ACTIONS) == expected_terminal
```

- [ ] **Step 2: Assert the terminal mapping envelope.**

```python
for source in sorted(expected_terminal):
    mapped = audit._map_callback(source, "callback_data", evidence, routes)
    assert mapped["target"] == "TELEGRAM_ONLY"
    assert mapped["status"] == "TELEGRAM_ONLY"
    assert mapped["classification"] == "admin"
    assert mapped["resolution"] == "archive_pending_state_requires_telegram_context"
    assert "BOT_ARCHIVE_PENDING_STATE" in mapped["source_dispositions"]
    assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
    assert "archive_authority" not in mapped
    assert "archive_launch_mode" not in mapped
```

- [ ] **Step 3: Assert exactness and drift visibility.**

```python
for source in (
    "ARCHIVE|BACK_DEPARTMENT",
    "archive|back_department|future",
    "archive|edit ",
    "ARCHIVE|ROOT",
):
    mapped = audit._map_callback(source, "callback_data", evidence, routes)
    assert mapped["target"] == "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED"
    assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert "archive_authority" not in mapped
    assert "archive_launch_mode" not in mapped

template = audit._map_callback_template("archive|dept|{*}", evidence, routes)
assert template["target"] == "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED"
assert template["status"] == "NEEDS_FEATURE_DISPOSITION"
```

- [ ] **Step 4: Assert frozen report closure while preserving dynamic drift.**

```python
archive_records = [
    item for item in parity_gap["callback_mappings"]
    if item["source"] in audit.ARCHIVE_PENDING_STATE_TELEGRAM_ONLY_ACTIONS
]
assert len(archive_records) == 9
assert all(item["target"] == "TELEGRAM_ONLY" and item["status"] == "TELEGRAM_ONLY" for item in archive_records)
archive_backlog = next(item for item in parity_gap["feature_disposition_backlog"] if item["family"] == "archive")
assert archive_backlog["count"] == 2
assert archive_backlog["sample_sources"] == ["archive|dept|{*}"]
```

- [ ] **Step 5: Run the red tests.**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py -k 'archive_literals or current_migration_evidence'
```

Expected: failure because the pending-state terminal catalog and terminal mapping do not exist.

### Task 2: Implement the finite Archive terminal mapper

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py` near the Archive registries and `_map_archive_callback`.

- [ ] **Step 1: Add the raw finite catalog.**

```python
ARCHIVE_PENDING_STATE_TELEGRAM_ONLY_ACTIONS = frozenset({
    "archive|back_department",
    "archive|change_dept",
    "archive|discard_to_dept",
    "archive|edit",
})
```

- [ ] **Step 2: Add a terminal-only mapping helper.**

```python
def _archive_pending_state_telegram_only_mapping(identifier, source_kind, evidence):
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "TELEGRAM_ONLY",
        "classification": "admin",
        "status": "TELEGRAM_ONLY",
        "resolution": "archive_pending_state_requires_telegram_context",
        "source_dispositions": (
            "BOT_ADMIN_ONLY",
            "BOT_ARCHIVE_PENDING_STATE",
            "TELEGRAM_ARCHIVE_STATE_TRANSITION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "The frozen Bot action reads or changes Telegram-local Archive pending state; the Web Archive accepts no Bot state, identifier, file or mutation.",
        "evidence": evidence,
    }
```

- [ ] **Step 3: Make every finite lookup raw and exact.**

Use `raw_identifier = str(identifier or "")` for fresh-navigation, existing Telegram-only and new terminal-catalog membership. If a case-mixed value reaches the Archive namespace through normalized routing, return the ordinary source-review mapping; never grant it navigation or terminal status. Keep `archive|dept|{*}` and every unlisted raw value source-review-required.

- [ ] **Step 4: Run the red tests green.**

Run the Task 1 command. Expected: pass.

### Task 3: Update the migration contract and evidence

**Files:**
- Modify: `docs/migration/ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md`.
- Regenerate: `docs/migration/*.md` and `reports/migration/*.json` from the frozen Bot baseline.
- Modify: `docs/migration/TEST_EVIDENCE.md` only if its current safe-disposition metric changes.

- [ ] **Step 1: Update the Archive boundary table.**

Replace the source-review row for the four exact pending-state callbacks with `TELEGRAM_ONLY`, state that matching is raw/case-sensitive, and explicitly preserve the dynamic `archive|dept|{*}` source-review boundary.

- [ ] **Step 2: Regenerate frozen static evidence.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'C:\Users\toann\Documents\Codex\2026-05-31\files-mentioned-by-the-user-bot\toanaas-hotfix-28ff87f' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: static-only audit completion; no Bot import/start or live request.

- [ ] **Step 3: Synchronize human-readable evidence.**

Read `mapping_coverage_percent` from `reports/migration/parity_gap.json` and replace only the current safe-disposition percentage in `docs/migration/TEST_EVIDENCE.md`. Do not alter historical metrics.

### Task 4: Verify, review, and integrate

**Files:**
- Verify: `scripts/migration/audit_bot_to_web.py`, `tests/test_migration_audit.py`, `docs/migration`, `reports/migration`.

- [ ] **Step 1: Run targeted tests.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py tests/test_copyfast_admin_document_archive.py
```

- [ ] **Step 2: Run static checks.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check
git status --short --untracked-files=all
```

- [ ] **Step 3: Inspect the staged scope.**

```powershell
git add docs/superpowers/specs/2026-08-01-archive-terminal-callback-catalog-design.md docs/superpowers/plans/2026-08-01-archive-terminal-callback-catalog.md scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration reports/migration
git diff --cached --check
git diff --cached --name-only
```

Expected: only the Archive audit contract, test, evidence and plan files; no Bot, runtime Archive, provider, wallet/payment, Video or coordinated files.

- [ ] **Step 4: Perform spec-compliance then code-quality review.**

Review exact case sensitivity, terminal shape, dynamic drift visibility, frozen report counts, documentation consistency and staged scope. Resolve all important findings before merge.

- [ ] **Step 5: Commit, push, create PR, merge only after CI green, then verify Railway.**

```powershell
git commit -m "Audit Archive pending callbacks as Telegram-only"
git push -u origin feature/p0-webapp-copyfast262-archive-terminal-catalog
```

After merge, verify only Railway deployment SHA, `/health`, and a protected public route boundary. Do not enable Archive flags or call provider, PayOS, wallet, Telegram, job or private Archive endpoints.

## Plan self-review

- Every finite source is named exactly and no dynamic source is promoted.
- Case variants, whitespace and suffixes remain source-review-required.
- Existing fresh navigation and preview/save terminal policies remain intact.
- The task is audit/docs only and makes no runtime or external-effect claim.
