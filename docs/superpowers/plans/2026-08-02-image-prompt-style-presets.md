# Image Prompt Composer Style Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe, Web-native style presets to Image Prompt Composer without changing its text-only, provider-free boundary.

**Architecture:** A strict `style_preset` field selects server-owned style text from goal/language catalogues.  Only `custom` accepts the existing bounded style text.  The portal disables and hides custom input until required, and its save source/result matching includes the exact semantic selection.

**Tech Stack:** FastAPI, Pydantic v2, Python pytest, vanilla portal JavaScript/CSS.

---

### Task 1: Specify the server contract with failing API tests

**Files:**
- Modify: `tests/test_copyfast_image_prompt_composer.py`
- Modify: `tests/test_image_prompt_composer_portal_contracts.py`

- [ ] **Step 1: Write failing API tests for bounded preset resolution**

```python
response = client.post(path, headers={"X-CSRF-Token": csrf}, json=composer_payload(style="", style_preset="suggestion_1"))
assert response.status_code == 200
assert response.json()["data"]["composer"]["style_preset"] == "suggestion_1"
assert response.json()["data"]["composer"]["style"]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest -q tests/test_copyfast_image_prompt_composer.py -k style_preset`

Expected: FAIL because `style_preset` is currently forbidden and result has no preset field.

- [ ] **Step 3: Add failing contract assertions for the portal selection boundary**

```python
assert 'IMAGE_PROMPT_COMPOSER_STYLE_PRESET_OPTIONS' in PORTAL
assert 'function synchronizeImagePromptComposerStylePreset(form)' in PORTAL
assert '"style_preset"' in INTEGRATION
```

- [ ] **Step 4: Verify RED**

Run: `python -m pytest -q tests/test_image_prompt_composer_portal_contracts.py`

Expected: FAIL because the selection control and strict source matching do not exist.

### Task 2: Implement the server-owned semantic preset resolver

**Files:**
- Modify: `copyfast_image_studio.py`
- Test: `tests/test_copyfast_image_prompt_composer.py`

- [ ] **Step 1: Add `style_preset` allowlist and validation**

```python
PROMPT_COMPOSER_STYLE_PRESETS = frozenset({"auto", "suggestion_1", "suggestion_2", "suggestion_3", "custom"})

@field_validator("style_preset")
@classmethod
def validate_style_preset(cls, value: str) -> str:
    normalized = _line(value, label="Preset phong cách", minimum=1, maximum=32).lower()
    if normalized not in PROMPT_COMPOSER_STYLE_PRESETS:
        raise ValueError("Preset phong cách không hợp lệ")
    return normalized
```

- [ ] **Step 2: Resolve only server catalogue values outside custom mode**

```python
def _prompt_composer_style(goal_code: str, language: str, style_preset: str, custom_style: str) -> str:
    if style_preset == "custom":
        return custom_style
    return _prompt_composer_style_preset(goal_code, language, style_preset)
```

- [ ] **Step 3: Include the semantic preset in result and Memory recomputation**

Add the field to `ImagePromptComposerResult`, its validators, result dump and the
existing request-derived Memory handoff.  Do not alter any no-engine boundary.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest -q tests/test_copyfast_image_prompt_composer.py -k style_preset`

Expected: PASS.

### Task 3: Implement accessible portal selection and strict handoff matching

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal.css`
- Test: `tests/test_image_prompt_composer_portal_contracts.py`

- [ ] **Step 1: Render a labelled Web-native preset select and custom field**

Use select values `auto`, `suggestion_1`, `suggestion_2`, `suggestion_3`, and
`custom`; give the textarea `data-image-prompt-composer-custom-style`, put it in
a field wrapper with `data-image-prompt-composer-custom-style-field`, and add a
polite status element.

- [ ] **Step 2: Synchronize visibility and disabled/required state**

```javascript
const customMode = String(preset.value || "auto") === "custom";
custom.disabled = preset.disabled || !customMode;
custom.required = customMode;
field.hidden = !customMode;
```

Wire it on `change` and after portal render.  The request payload must emit an
empty `style` for all non-custom choices and include `style_preset`.

- [ ] **Step 3: Require exact `style_preset` agreement for result and Memory save**

Add the field to all exact-shape checks, safe result projection, and
`imagePromptComposerMemorySaveSourceMatchesResult`.  A browser must not save a
receipt whose semantic choice differs from the visible result.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest -q tests/test_image_prompt_composer_portal_contracts.py`

Expected: PASS.

### Task 4: Review and merge the focused slice

**Files:**
- Verify: `copyfast_image_studio.py`, `static/portal/portal.js`, `static/portal/integration.js`, `static/portal/portal.css`, and the focused tests

- [ ] **Step 1: Run focused regression tests**

Run: `python -m pytest -q tests/test_copyfast_image_prompt_composer.py tests/test_image_prompt_composer_portal_contracts.py tests/test_image_operation_portal_contracts.py`

Expected: PASS.

- [ ] **Step 2: Compile and inspect the diff**

Run: `python -m py_compile copyfast_image_studio.py && git diff --check && git diff --stat`

Expected: no syntax errors, whitespace errors, or unrelated files.

- [ ] **Step 3: Commit and create one PR**

```bash
git add copyfast_image_studio.py static/portal/portal.js static/portal/integration.js static/portal/portal.css tests docs/superpowers
git commit -m "Add Web-native image prompt style presets"
git push -u origin feature/p0-webapp-copyfast266-image-prompt-style-presets
```

Create and merge a single focused PR only after checks are green.
