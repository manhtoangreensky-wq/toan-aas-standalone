# Image Prompt Composer Variant Catalogue Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Match the Bot's visible three-item Image Prompt variant catalogue in the Web-native request-only composer.

**Architecture:** Extract a narrow pure server helper taking `subject`, resolved `style`, normalized `ratio`, and `language`.  It emits only the Bot-visible sales/premium/viral strings and is called by the existing result composition; no new API field, route, persistence or execution path is added.

**Tech Stack:** FastAPI, Pydantic v2, Python pytest.

---

### Task 1: Lock exact Bot-visible variants in a failing API test

**Files:**
- Modify: `tests/test_copyfast_image_prompt_composer.py`

- [ ] **Step 1: Add expected lists for Vietnamese and English**

```python
assert composer["variants"] == [
    f"{subject}, ảnh bán hàng làm rõ sản phẩm và lợi ích chính, studio sạch, 9:16, ánh sáng premium, chi tiết cao, không watermark",
    f"{subject}, key visual thương hiệu cao cấp, phong cách {style}, bố cục tinh tế, 9:16, ánh sáng luxury, chất lượng cao, không chữ thừa",
    f"{subject}, ảnh viral nổi bật mạng xã hội, điểm nhìn mạnh, bố cục giàu năng lượng, 9:16, dễ dừng lướt, chủ thể sạch, không watermark",
]
```

Add the equivalent English list and assert both routes remain `status=200`,
`status="draft"`, and have exactly three variants.

- [ ] **Step 2: Verify RED**

```powershell
$python = 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe'
& $python -m pytest -q tests/test_copyfast_image_prompt_composer.py -k bot_variant_catalog
```

Expected: FAIL because the current Web strings are similar but not the Bot
catalogue.

### Task 2: Add a pure server resolver and route result composition through it

**Files:**
- Modify: `copyfast_image_studio.py`
- Test: `tests/test_copyfast_image_prompt_composer.py`

- [ ] **Step 1: Implement the resolver**

```python
def _prompt_composer_variants(*, subject: str, style: str, ratio: str, language: str) -> list[str]:
    if language == "vi":
        return [
            f"{subject}, ảnh bán hàng làm rõ sản phẩm và lợi ích chính, studio sạch, {ratio}, ánh sáng premium, chi tiết cao, không watermark",
            f"{subject}, key visual thương hiệu cao cấp, phong cách {style}, bố cục tinh tế, {ratio}, ánh sáng luxury, chất lượng cao, không chữ thừa",
            f"{subject}, ảnh viral nổi bật mạng xã hội, điểm nhìn mạnh, bố cục giàu năng lượng, {ratio}, dễ dừng lướt, chủ thể sạch, không watermark",
        ]
    return [
        f"{subject}, product-led sales hero image, clear benefit, clean studio, {ratio}, premium lighting, high detail, no watermark",
        f"{subject}, premium brand key visual, {style}, refined composition, {ratio}, luxury lighting, high quality, no extra text",
        f"{subject}, viral social media visual, bold focal point, energetic composition, {ratio}, scroll-stopping, clean subject, no watermark",
    ]
```

- [ ] **Step 2: Replace the inline list in `_compose_image_prompt`**

```python
variants = _prompt_composer_variants(subject=subject, style=style, ratio=ratio, language=language)
```

Do not alter short/detailed/negative prompts, the request model, Memory save
payload, boundary facts, or any external route.

- [ ] **Step 3: Verify GREEN**

Run the Task 1 command. Expected: PASS.

### Task 3: Regression gate and focused PR

**Files:**
- Verify: `copyfast_image_studio.py`, `tests/test_copyfast_image_prompt_composer.py`, these docs

- [ ] **Step 1: Run focused gates**

```powershell
& $python -m pytest -q tests/test_copyfast_image_prompt_composer.py tests/test_image_prompt_composer_portal_contracts.py tests/test_image_operation_portal_contracts.py
& $python -m py_compile copyfast_image_studio.py
git diff --check
```

Expected: all focused tests pass, no syntax or whitespace errors, and no Bot,
provider, PayOS, wallet, job or delivery file changes.

- [ ] **Step 2: Commit and create PR**

```powershell
git add copyfast_image_studio.py tests/test_copyfast_image_prompt_composer.py docs/superpowers
git commit -m "Map Web image prompt variant catalog"
git push -u origin feature/p0-webapp-copyfast268-image-prompt-variant-catalog
```

Merge only after review and CI pass.
