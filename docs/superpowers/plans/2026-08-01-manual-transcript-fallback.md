# Manual Transcript Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the one known-broken Bot transcript menu literal into a fresh, guarded, manual Subtitle Studio fallback without replaying any Bot state or claiming translation execution.

**Architecture:** The static migration auditor owns one exact private descriptor for `menu|translation_transcript`. It returns `/subtitle-studio` as a `COPIED_GUARDED` compatibility surface and emits only redacted boundary metadata. The public Web capability catalog remains unchanged, while the migration contract explains that the Bot branch is broken and the Web editor is a new manual workspace.

**Tech Stack:** Python 3.12 static audit generator, pytest, Markdown migration contracts.

---

### Task 1: Prove the required fallback before implementation

**Files:**
- Modify: `tests/test_migration_audit.py:4559-4715`
- Test: `tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions`

- [ ] **Step 1: Write the failing test**

Replace the known-broken assertion block with this exact expected behavior:

```python
    assert audit.TRANSLATION_KNOWN_BROKEN_MENU_ACTIONS == {"menu|translation_transcript"}
    assert "menu|translation_transcript" not in audit.MENU_ACTION_REGISTRY
    transcript = audit._map_callback(
        "menu|translation_transcript", "callback_data", {"file": "bot.py", "line": 1}, routes
    )
    assert transcript["target"] == "/subtitle-studio"
    assert transcript["status"] == "COPIED_GUARDED"
    assert transcript["resolution"] == "reviewed_known_broken_translation_transcript_manual_fallback"
    assert transcript["translation_fallback_capability_key"] == "subtitle_studio"
    assert transcript["source_dispositions"] == (
        "BOT_KNOWN_BROKEN_TRANSLATION_TRANSCRIPT",
        "BOT_PENDING_TEXT_OR_MEDIA_STATE",
        "FRESH_SIGNED_WEB_MANUAL_TRANSCRIPT_FALLBACK",
        "NO_RAW_BOT_CALLBACK_OR_PENDING_SOURCE_TO_BROWSER",
        "NO_ASR_TRANSLATION_TTS_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION",
        "NO_RUNTIME_CLAIM",
    )
    case_variant = audit._map_callback(
        "MENU|TRANSLATION_TRANSCRIPT", "callback_data", {"file": "bot.py", "line": 1}, routes
    )
    assert case_variant["target"] != "/subtitle-studio"
    assert case_variant["resolution"] != "reviewed_known_broken_translation_transcript_manual_fallback"
```

Add this public-catalog assertion after the existing serialized catalog check:

```python
    assert "translation_transcript" not in serialized_catalog
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest -q tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions
```

Expected: FAIL because the mapper still returns `BOT_TRANSLATION_TRANSCRIPT_KNOWN_BROKEN` with `NEEDS_FEATURE_DISPOSITION`.

### Task 2: Implement the exact guarded descriptor

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py:3524-3538`
- Modify: `scripts/migration/audit_bot_to_web.py:8275-8304`
- Test: `tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions`

- [ ] **Step 1: Add the private fallback descriptor**

Directly after `TRANSLATION_KNOWN_BROKEN_MENU_ACTIONS`, add the exact descriptor:

```python
TRANSLATION_KNOWN_BROKEN_MANUAL_FALLBACKS: dict[str, dict[str, Any]] = {
    "menu|translation_transcript": {
        "target": "/subtitle-studio",
        "capability_key": "subtitle_studio",
        "source_dispositions": (
            "BOT_KNOWN_BROKEN_TRANSLATION_TRANSCRIPT",
            "BOT_PENDING_TEXT_OR_MEDIA_STATE",
            "FRESH_SIGNED_WEB_MANUAL_TRANSCRIPT_FALLBACK",
            "NO_RAW_BOT_CALLBACK_OR_PENDING_SOURCE_TO_BROWSER",
            "NO_ASR_TRANSLATION_TTS_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": (
            "The frozen Bot stores a `transcript` pending source, but its translation callback accepts only voice, "
            "file and text before returning an unsupported-source alert. The Web fallback starts a blank signed "
            "manual Subtitle Studio workspace and receives no Telegram source, pending state or execution request."
        ),
    },
}
```

- [ ] **Step 2: Replace the mapper body**

Make `_map_known_broken_translation_menu_action` exact and return the guarded surface:

```python
    action = TRANSLATION_KNOWN_BROKEN_MANUAL_FALLBACKS.get(identifier)
    if action is None:
        return None
    target = str(action["target"])
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": target,
        "classification": "customer",
        "status": _mapping_status(target, existing_routes, telegram_only=False),
        "resolution": "reviewed_known_broken_translation_transcript_manual_fallback",
        "source_dispositions": tuple(action["source_dispositions"]),
        "source_evidence": str(action["source_evidence"]),
        "translation_fallback_capability_key": str(action["capability_key"]),
        "evidence": evidence,
    }
```

Update the function signature to accept `existing_routes: set[str]`, and pass `existing_routes` from `_map_callback`.

- [ ] **Step 3: Run test to verify it passes**

Run:

```powershell
python -m pytest -q tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions
```

Expected: PASS.

### Task 3: Make the migration contract discoverable and regenerate evidence

**Files:**
- Modify: `docs/migration/TRANSLATION_MENU_BOUNDARY_CATALOG.md:42-58`
- Modify: `scripts/migration/audit_bot_to_web.py:12267-12420`
- Modify: `reports/migration/bot_inventory.json`
- Modify: `reports/migration/web_inventory.json`
- Modify: `reports/migration/parity_gap.json`
- Modify: `reports/migration/preflight.json`
- Modify: generated `docs/migration/{README.md,FEATURE_PARITY_MATRIX.md,KNOWN_GAPS_AND_GUARDS.md,inventory.md,known-gaps.md,parity-matrix.md}`
- Test: `tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions`

- [ ] **Step 1: Update the translation boundary section**

Replace the current known-broken paragraph with wording that preserves the Bot failure and separates it from the new fallback:

```markdown
`menu|translation_transcript` remains a source-proven broken Bot branch: it stores
`transcript` pending state and later returns an unsupported-source alert. The one
exact lower-case literal may instead open a fresh guarded `/subtitle-studio`
workspace with a blank Web-owned manual transcript. It transfers no callback,
Telegram identity, pending source, media/file, language target, provider request,
job, Xu/wallet, PayOS/payment, output or delivery state. The workspace does not
perform ASR, translation, TTS, dubbing or a provider call and does not prove that
the Bot branch worked. Case variants, suffixes and unknown values stay fail-closed.
```

- [ ] **Step 2: Add the README contract link**

Add this generated README bullet next to other callback contracts:

```python
        + "- [`TRANSLATION_MENU_BOUNDARY_CATALOG.md`](TRANSLATION_MENU_BOUNDARY_CATALOG.md) — exact known-broken Bot transcript fallback to a fresh guarded manual Subtitle Studio workspace; it never replays Bot state or claims translation execution.\n"
```

- [ ] **Step 3: Regenerate static artifacts**

Run:

```powershell
python scripts/migration/audit_bot_to_web.py `
  --bot-root "D:\\TOANAAS\\bot telegram" `
  --web-root . `
  --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4
```

Expected: exit 0; generated JSON reflects `COPIED_GUARDED` for the one exact callback and no secret values.

- [ ] **Step 4: Run focused contract checks**

Run:

```powershell
python -m pytest -q tests/test_migration_audit.py::test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions tests/test_copyfast_subtitle_workspace.py
git diff --check
```

Expected: all selected tests pass and no whitespace errors.

- [ ] **Step 5: Commit**

```powershell
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/TRANSLATION_MENU_BOUNDARY_CATALOG.md docs/migration/README.md docs/migration/FEATURE_PARITY_MATRIX.md docs/migration/KNOWN_GAPS_AND_GUARDS.md docs/migration/inventory.md docs/migration/known-gaps.md docs/migration/parity-matrix.md reports/migration/bot_inventory.json reports/migration/web_inventory.json reports/migration/parity_gap.json reports/migration/preflight.json docs/superpowers/specs/2026-08-01-menu-terminal-disposition-catalog-design.md docs/superpowers/plans/2026-08-01-manual-transcript-fallback.md
git commit -m "feat: add guarded manual transcript fallback"
```
