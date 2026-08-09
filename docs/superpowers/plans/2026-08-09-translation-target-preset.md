# Translation Target Preset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a closed Vietnamese/English/Chinese target-pair chooser to the fresh Web-native Subtitle Studio translation intake without creating a provider or Bot execution path.

**Architecture:** The portal renders a pair selector only when the route is `/subtitle-studio/new` and its already allowlisted intent is `translation`. The browser integration validates the same finite pair catalog and projects it into the existing `source_language`/`target_language` request fields before the current CSRF/idempotency path. No server schema, bridge, wallet, payment, Bot, provider or job code changes.

**Tech Stack:** FastAPI application, static JavaScript portal/integration layers, pytest static contracts.

---

### Task 1: Define the safety contract first

**Files:**

- Modify: `tests/test_subtitle_studio_portal_contracts.py`
- Modify: `docs/migration/SUBTITLE_TRANSCRIPT_WORKSPACE_CONTRACT.md`
- Create: `docs/migration/TRANSLATION_WEB_NATIVE_TARGET_PRESET_CONTRACT.md`

- [ ] **Step 1: Write the failing test**

```python
def test_translation_target_preset_is_closed_and_web_native() -> None:
    assert 'const SUBTITLE_STUDIO_TRANSLATION_PRESETS' in PORTAL
    assert 'function subtitleStudioTranslationPresetFromQuery(page)' in PORTAL
    assert 'const SUBTITLE_STUDIO_TRANSLATION_PRESET_KEYS' in INTEGRATION
    assert 'WEB_SUBTITLE_TRANSLATION_PRESET_INVALID' in INTEGRATION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_subtitle_studio_portal_contracts.py::test_translation_target_preset_is_closed_and_web_native`

Expected: FAIL because the target preset contract does not exist yet.

- [ ] **Step 3: Document the exact boundary**

Record that the select creates only a new Web-owned manual project, and that provider/bridge/job/payment/Bot state remains guarded.

- [ ] **Step 4: Run test to verify it still fails for the missing implementation**

Run: `python -m pytest -q tests/test_subtitle_studio_portal_contracts.py::test_translation_target_preset_is_closed_and_web_native`

Expected: FAIL because the portal/integration implementation remains absent.

### Task 2: Add the closed portal and request projection

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Test: `tests/test_subtitle_studio_portal_contracts.py`

- [ ] **Step 1: Add the portal-only preset chooser**

```javascript
const SUBTITLE_STUDIO_TRANSLATION_PRESETS = Object.freeze([
  ["vi-en", "Tiếng Việt → English", "vi", "en"],
  ["en-vi", "English → Tiếng Việt", "en", "vi"],
  ["vi-zh", "Tiếng Việt → 中文", "vi", "zh"],
  ["zh-vi", "中文 → Tiếng Việt", "zh", "vi"],
  ["en-zh", "English → 中文", "en", "zh"],
  ["zh-en", "中文 → English", "zh", "en"]
]);
```

Render this select only for the new translation route. Preserve generic editable source/target labels everywhere else.

- [ ] **Step 2: Project the selected key through the existing request**

```javascript
const preset = SUBTITLE_STUDIO_TRANSLATION_PRESET_KEYS.get(pairKey);
if (!preset) throw new Error("WEB_SUBTITLE_TRANSLATION_PRESET_INVALID");
return { source_language: preset.source, target_language: preset.target };
```

The parser must run before `api("/subtitle-studio/projects", ...)` and must never create a network/bridge/provider fallback.

- [ ] **Step 3: Run focused contract test**

Run: `python -m pytest -q tests/test_subtitle_studio_portal_contracts.py::test_translation_target_preset_is_closed_and_web_native`

Expected: PASS.

### Task 3: Verify regression boundaries and prepare integration

**Files:**

- Modify if required by the audit: `reports/migration/*.json`
- Test: `tests/test_subtitle_studio_portal_contracts.py`
- Test: `tests/test_copyfast_subtitle_workspace.py`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Run Subtitle Studio regression tests**

Run: `python -m pytest -q tests/test_subtitle_studio_portal_contracts.py tests/test_copyfast_subtitle_workspace.py`

Expected: PASS with no provider, wallet, payment or Bot side effects.

- [ ] **Step 2: Refresh static audit evidence only if source fingerprint/checks require it**

Run: `python scripts/migration/audit_bot_to_web.py --help`

Use the documented static-only invocation; do not import/start Bot or provider code.

- [ ] **Step 3: Verify final diff**

Run: `git diff --check` and the repository JavaScript syntax check used by existing CI.

Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add static/portal/portal.js static/portal/integration.js tests/test_subtitle_studio_portal_contracts.py docs/migration docs/superpowers reports/migration
git commit -m "Add web-native translation target presets"
```
