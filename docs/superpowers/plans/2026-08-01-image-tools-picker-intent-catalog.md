# Image Tools Picker-Intent Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify thirteen exact, low-side-effect Image Tools picker literals as fresh signed Web navigation while proving the picker value is discarded and every other `imgtool|*` value stays fail-closed.

**Architecture:** Keep the existing direct-tool registry unchanged.  Add a second raw-key `IMGTOOL_PICKER_INTENT_FRESH_WEB_NAVIGATION_ACTIONS` registry in the static auditor.  The existing mapper checks both dictionaries without normalization; picker matches reuse the existing fresh-navigation envelope but identify their source mode as `BOT_PICKER_INTENT_DISCARDED`.  Generated migration evidence lists both finite catalogs and maintains the residual state-machine boundary.  Bot numbered style suggestions and AI edit types remain source-review-required because the Web has no semantically equivalent picker/runtime.

**Tech Stack:** Python static AST audit, pytest, generated Markdown/JSON migration evidence.

---

### Task 1: Write red picker-intent contracts

**Files:**

- Modify: `tests/test_migration_audit.py:440-454` and `tests/test_migration_audit.py:3350-3520`.
- Test: `tests/test_migration_audit.py::test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes`.

- [ ] **Step 1: Define the desired exact picker registry in the existing Image Tools test.**

```python
imgtool_picker_intent_navigation = {
    "imgtool|prompt_goal|product": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_goal|ad": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_goal|cinematic": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|1x1": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|9x16": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|16x9": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|4x5": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|3x4": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|prompt_ratio|4x3": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|resize_pixels|1024x1024": ("/image/resize", "web_image_resize"),
    "imgtool|resize_pixels|1920x1080": ("/image/resize", "web_image_resize"),
    "imgtool|resize_pixels|1080x1920": ("/image/resize", "web_image_resize"),
    "imgtool|resize_pixels|1080x1350": ("/image/resize", "web_image_resize"),
}
assert set(audit.IMGTOOL_PICKER_INTENT_FRESH_WEB_NAVIGATION_ACTIONS) == set(imgtool_picker_intent_navigation)
```

- [ ] **Step 2: Assert the exact no-transfer envelope.**

```python
assert mapped["target"] == target
assert mapped["status"] == "NAVIGATION_ONLY"
assert mapped["resolution"] == "reviewed_imgtool_fresh_web_navigation"
assert mapped["imgtool_navigation_source_mode"] == "BOT_PICKER_INTENT_DISCARDED"
assert "BOT_PICKER_INTENT_DISCARDED" in mapped["source_dispositions"]
assert "?" not in mapped["target"] and "#" not in mapped["target"]
```

Keep the current direct-entry expected dispositions unchanged.  Picker records
also retain `NO_RAW_BOT_CALLBACK_OR_IMAGE_STATE_TO_BROWSER`,
`BOT_IMAGE_TOOL_PENDING_OR_RESULT_STATE_NOT_REPLAYED`,
`NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION`, and `NO_RUNTIME_CLAIM`.

- [ ] **Step 3: Add negative and synthetic-audit coverage.**

Assert `IMGTOOL|PROMPT_GOAL|PRODUCT`, `imgtool|prompt_style|1`,
` imgtool|prompt_style|1`, `imgtool|prompt_ratio|1x1|future`, `imgtool|resize_pixels|999x999`,
`imgtool|prompt_goal_custom`, `imgtool|edit_type|product_beauty`,
`imgtool|edit_ai`, `imgtool|prompt_tier|basic`, and all corresponding
`{*}` templates remain `IMGTOOL_SOURCE_REVIEW_REQUIRED`.  Extend the
synthetic Bot source with one direct literal from each reviewed family and
one f-string/template negative; assert only the exact raw literals produce
the picker-intent source mode.

- [ ] **Step 4: Extend frozen evidence assertions.**

```python
reviewed_sources = set(audit.IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS) | set(
    audit.IMGTOOL_PICKER_INTENT_FRESH_WEB_NAVIGATION_ACTIONS
)
assert {mapping["source"] for mapping in imgtool_navigation_mappings} == reviewed_sources
```

- [ ] **Step 5: Run the red test.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes
```

Expected: FAIL because the second raw catalog and source mode do not exist.

### Task 2: Implement a raw finite catalog

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:7632-7741`.

- [ ] **Step 1: Add a separate raw dictionary for the thirteen listed literals.**

```python
IMGTOOL_PICKER_INTENT_FRESH_WEB_NAVIGATION_ACTIONS: dict[str, dict[str, str]] = {
    "imgtool|prompt_goal|product": {
        "target": "/image/prompt-composer",
        "web_image_tool_intent": "web_image_prompt_composer",
    },
    # Repeat the twelve exact literals from Task 1; no prefix, regex, split,
    # lower/casefold, parser or generated key is permitted.
}
```

- [ ] **Step 2: Make the helper distinguish a discarded picker from a direct tool entry.**

```python
action = IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS.get(identifier)
source_mode = "DIRECT_TOOL_ENTRY"
if action is None:
    action = IMGTOOL_PICKER_INTENT_FRESH_WEB_NAVIGATION_ACTIONS.get(identifier)
    source_mode = "BOT_PICKER_INTENT_DISCARDED"
if action is None:
    return None
```

For picker matches, add exactly `BOT_PICKER_INTENT_DISCARDED` to the source
dispositions and a source-evidence sentence saying the Bot value is discarded
and every Web field, Asset Vault choice and confirmation is made again.  Keep
the existing direct-entry record shape and all fallback behavior intact.

- [ ] **Step 3: Run the focused test green.**

Run the Task 1 command.  Expected: PASS.

### Task 3: Render truthful frozen-baseline evidence

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py:12584-12610`, the Image Tools
  README/Payos map strings near `12875`, `13778` and `13938`.
- Regenerate: `docs/migration/*.md`, `reports/migration/*.json`.
- Modify: `docs/migration/TEST_EVIDENCE.md` only if the regenerated current
  parity percentage changes.

- [ ] **Step 1: Include both registries in Image Tools contract rows.**

Each picker-intent row must say that its Bot selection is discarded, no
callback or state is prefilled, and the Web route starts only after a signed
session.  Update generated explanatory count from seventeen to the computed
combined finite count; do not alter historical evidence.

- [ ] **Step 2: Regenerate from the frozen Git baseline.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
```

Expected: static-only JSON reports describe the requested SHA and no Bot
import, provider, payment, Telegram or Web runtime request occurs.

- [ ] **Step 3: Synchronize the current human-readable metric.**

Copy only the current `mapping_coverage_percent` from the generated
`reports/migration/parity_gap.json` into `docs/migration/TEST_EVIDENCE.md` if
the existing consistency test requires it.

### Task 4: Verify, review and integrate

**Files:**

- Verify: audit script, migration test, focused generated evidence, Image
  Operations contracts, design and plan.

- [ ] **Step 1: Run focused verification.**

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_migration_audit.py tests/test_image_operation_portal_contracts.py tests/test_copyfast_image_operations.py
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile scripts/migration/audit_bot_to_web.py
git diff --check
```

- [ ] **Step 2: Conduct two independent reviews.**

First check the exact source list, fail-closed negative variants, discard-only
semantics and generated evidence.  Then check code quality, documentation
counts and changed-file scope.  Resolve all important findings and re-review
any fix.

- [ ] **Step 3: Stage only scope files, commit and integrate.**

```powershell
git add docs/superpowers/specs/2026-08-01-image-tools-picker-intent-catalog-design.md docs/superpowers/plans/2026-08-01-image-tools-picker-intent-catalog.md scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration reports/migration
git diff --cached --check
git diff --cached --name-only
git commit -m "Catalog safe Image Tools picker navigation"
```

Push `feature/p0-webapp-copyfast265-imgtool-picker-intent-catalog`, create a
single PR, and merge only after the Web App quality gate is green.  This
static-only audit plan ends at integration; Railway deployment, public
`/health` and protected-route smoke checks are separate release operations and
must not be cited as audit/runtime parity evidence.

## Plan self-review

- All thirteen literals are written exactly and each target already exists.
- Picker choices are discarded, not carried to Web as a query, form, browser
  storage, API payload, database value or execution request.
- Dynamic, custom, AI, confirmation, stateful and case/suffix variants remain
  `IMGTOOL_SOURCE_REVIEW_REQUIRED`.
- Scope excludes `bot.py`, runtime/provider/payment/wallet/job code, Video,
  Motion, skills/capabilities and LocalVideoStudio-owned files.
