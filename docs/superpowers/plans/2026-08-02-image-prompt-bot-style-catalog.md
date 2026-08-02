# Image Prompt Composer Bot Style Catalogue Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map the Bot's visible image-style catalogue into existing Web-native `suggestion_1..3` values without importing Telegram transport or execution state.

**Architecture:** Keep the five-value Web preset contract.  Preserve the existing `auto` defaults and `custom` free-text path; replace only the server-owned three-suggestion resolver with a goal/language catalogue that follows the Bot's visible choices and product fallback for custom goals.

**Tech Stack:** FastAPI, Pydantic v2, Python pytest, vanilla portal JavaScript contract tests.

---

### Task 1: Specify exact catalogue parity with API tests

**Files:**
- Modify: `tests/test_copyfast_image_prompt_composer.py`
- Verify: `tests/test_image_prompt_composer_portal_contracts.py`

- [ ] **Step 1: Add a failing parity table for each server-owned suggestion**

```python
expected = {
    "vi": {
        "product": ["Studio sạch đẹp", "Luxury showroom", "Lifestyle đời thường"],
        "ad": ["Bán hàng trực tiếp", "Premium brand", "Viral/TikTok"],
        "cinematic": ["Cinematic ánh sáng mạnh", "Sci-fi/công nghệ tương lai", "Fantasy/cyberpunk"],
    },
    "en": {
        "product": ["Clean studio", "Luxury showroom", "Lifestyle everyday scene"],
        "ad": ["Direct sales", "Premium brand", "Viral/TikTok"],
        "cinematic": ["Strong cinematic lighting", "Sci-fi/future tech", "Fantasy/cyberpunk"],
    },
}
```

For every language/goal/index, post a signed CSRF request with empty `style`
and `style_preset=f"suggestion_{index}"`; assert `200`, semantic preset echo
and exact resolved style.  Repeat the product list for `goal_code=custom`
with a valid `custom_goal`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
$python = 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe'
& $python -m pytest -q tests/test_copyfast_image_prompt_composer.py -k bot_style_catalog
```

Expected: FAIL because the current generic Web catalogue does not equal the
Bot-visible direction table.

### Task 2: Resolve semantic Web presets through the copied visible catalogue

**Files:**
- Modify: `copyfast_image_studio.py`
- Test: `tests/test_copyfast_image_prompt_composer.py`

- [ ] **Step 1: Add a module-level immutable Web catalogue**

Use keys `vi|en → product|ad|cinematic → suggestion_1|suggestion_2|suggestion_3`.
Do not add callback strings, Bot imports, provider/model fields or state
fields.  Leave `_prompt_composer_default_style` intact for `auto`.

- [ ] **Step 2: Normalize only the catalogue lookup goal**

```python
catalog_goal = goal_code if goal_code in {"product", "ad", "cinematic"} else "product"
return PROMPT_COMPOSER_STYLE_SUGGESTION_CATALOG[language][catalog_goal][style_preset]
```

This gives custom goals the established product fallback while preserving the
customer's `goal_label` and `custom_goal` elsewhere in the prompt.

- [ ] **Step 3: Verify GREEN**

Run the Task 1 command.  Expected: PASS with exact strings for 2 languages,
3 concrete goals and custom fallback.

### Task 3: Retain strict portal and no-execution boundaries

**Files:**
- Verify: `static/portal/integration.js`
- Verify: `static/portal/portal.js`
- Verify: `tests/test_image_prompt_composer_portal_contracts.py`

- [ ] **Step 1: Add a static regression assertion**

Keep the existing client contract limited to `auto`, `suggestion_1`,
`suggestion_2`, `suggestion_3`, and `custom`.  Assert no `imgtool|prompt_style`
literal exists in Web integration code and no Bot/provider/payment route is
introduced.

- [ ] **Step 2: Run focused regression suite**

```powershell
& $python -m pytest -q tests/test_copyfast_image_prompt_composer.py tests/test_image_prompt_composer_portal_contracts.py tests/test_image_operation_portal_contracts.py
& $python -m py_compile copyfast_image_studio.py
git diff --check
```

Expected: all focused tests pass; no syntax or whitespace errors.

### Task 4: Review and ship one focused PR

**Files:**
- Verify: `copyfast_image_studio.py`, `tests/test_copyfast_image_prompt_composer.py`, `tests/test_image_prompt_composer_portal_contracts.py`, and these docs

- [ ] **Step 1: Review scope**

Confirm the diff contains no Bot source edit, callback transport value,
database migration, bridge, provider, PayOS, wallet, job or output change.

- [ ] **Step 2: Commit and create PR**

```powershell
git add copyfast_image_studio.py tests/test_copyfast_image_prompt_composer.py tests/test_image_prompt_composer_portal_contracts.py docs/superpowers
git commit -m "Map Web image prompt style catalog"
git push -u origin feature/p0-webapp-copyfast267-image-prompt-bot-style-catalog
```

Create and merge only after focused checks and code review pass.
