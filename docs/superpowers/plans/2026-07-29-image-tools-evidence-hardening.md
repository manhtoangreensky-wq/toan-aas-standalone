# Image Tools Evidence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the static migration auditor never promotes a mutable or indirect Telegram Image Tools callback into Web navigation evidence.

**Architecture:** Keep the reviewed Web-navigation registry finite and limited to concrete callback-data literals observed in frozen Bot SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`. Remove the default-parameter resolver because the frozen `image_editor_position_keyboard` call sites override its `back_callback`; `imgtool|editor_overlays` therefore remains a source-review boundary instead of an audited Web entry.

**Tech Stack:** Python static source audit, pytest, generated Markdown/JSON migration evidence.

---

### Task 1: Make the evidence contract fail closed

**Files:**
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Change the expected finite registry from eighteen to seventeen concrete raw literals.**

Remove `imgtool|editor_overlays` from the expected navigation dictionary and assert it maps to `IMGTOOL_SOURCE_REVIEW_REQUIRED` with `NEEDS_FEATURE_DISPOSITION` when passed directly to `_map_callback`.

- [ ] **Step 2: Extend the large-file synthetic source.**

Keep `back_callback="imgtool|editor_overlays"`, add a caller override and an in-function reassignment, and include comment/string near-misses. Assert no record for that source has resolution `reviewed_imgtool_fresh_web_navigation`; all actual reviewed records equal the seventeen-entry expected set.

- [ ] **Step 3: Run the focused test red.**

Run: `python -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes`

Expected: FAIL because the existing default-callback resolver still emits `imgtool|editor_overlays` as reviewed navigation evidence.

### Task 2: Remove mutable-default promotion and regenerate evidence

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Modify: `docs/superpowers/specs/2026-07-29-image-tools-fresh-navigation-design.md`
- Regenerate: `docs/migration/*`, `reports/migration/*`

- [ ] **Step 1: Remove `imgtool|editor_overlays` from `IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS`.**

No other key may be normalized, prefix matched, or inferred.

- [ ] **Step 2: Remove the default-parameter regexes, resolver, and resolver call.**

Do not replace them with variable, caller, assignment, comment, or string evaluation. Existing direct literals and existing generic source-review handling remain unchanged.

- [ ] **Step 3: Update the design guardrail.**

Document that `imgtool|editor_overlays` is indirect mutable Bot state in this frozen baseline and must remain source-review-required until a separate Web-native contract is reviewed.

- [ ] **Step 4: Run the focused test green and regenerate frozen-baseline evidence.**

Run the focused pytest command, then:

```powershell
python scripts/migration/audit_bot_to_web.py --bot-root C:\Users\toann\Documents\Codex\2026-05-31\files-mentioned-by-the-user-bot\toanaas-hotfix-28ff87f --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: exactly seventeen observed `reviewed_imgtool_fresh_web_navigation` sources and `imgtool|editor_overlays` absent from that set.

### Task 3: Verify and integrate the hotfix

**Files:**
- Verify: the task files above plus generated evidence.

- [ ] **Step 1: Synchronize `docs/migration/TEST_EVIDENCE.md`.**

Copy the current static counts and safe-disposition percentage from the regenerated reports, without changing historical evidence.

- [ ] **Step 2: Run targeted verification.**

Run `pytest -q tests/test_migration_audit.py tests/test_image_operation_portal_contracts.py`, `compileall`, Node syntax checks, `git diff --check`, and an explicit JSON assertion that every observed reviewed Image Tools source equals the seventeen-key registry.

- [ ] **Step 3: Review staged scope, commit, push, PR, merge only after the GitHub gate passes, and verify Railway's deployment SHA and `/health`.**

## Plan self-review

- The hotfix removes the exact mutable extraction identified by review rather than adding new inference.
- It preserves the Web-native image routes while preventing false Bot-to-Web parity claims.
- It does not touch Bot code, Web runtime, payments, providers, Video, skills, or LocalVideoStudio26-owned files.
