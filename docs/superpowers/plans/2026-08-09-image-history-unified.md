# Unified Web-native Image History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/image/history` show every verified, owner-scoped Web-native PNG operation, including Brand Overlay, without changing its private delivery or authority boundaries.

**Architecture:** The server continues to own the explicit combined-history allow-list and pagination. Add `image_brand_overlay` to that reviewed allow-list, then teach the existing combined-history renderer to render its redacted overlay settings with the same download guard already used on the dedicated Brand Overlay route. The dedicated `/image/brand-overlay` history remains unchanged.

**Tech Stack:** FastAPI, SQLite read models, vanilla JavaScript portal, pytest.

---

### Task 1: Lock the desired combined-history contract with failing tests

**Files:**

- Modify: `tests/test_copyfast_image_operations.py`
- Modify: `tests/test_operation_history_pagination.py`
- Modify: `tests/test_image_brand_overlay_contracts.py`
- Modify: `tests/test_image_operation_portal_contracts.py`

- [x] **Step 1: Change the Brand Overlay operation expectation from dedicated-only to both dedicated and combined history**

```python
combined_history = client.get("/api/v1/image-operations?limit=100")
assert combined_history.status_code == 200
assert operation["id"] in [item["id"] for item in combined_history.json()["data"]["items"]]
```

- [x] **Step 2: Expand the mixed pagination fixture to create one Brand Overlay operation and assert that the combined history contains only the three reviewed kinds**

```python
assert item["kind"] in {"image_resize", "image_enhance", "image_brand_overlay"}
assert set(combined_ids) == expected_history_ids
```

- [x] **Step 3: Update static contracts to require the reviewed three-kind server allow-list and a truthful Brand Overlay card in the combined portal history**

```python
assert "IMAGE_HISTORY_KINDS = frozenset({IMAGE_RESIZE_KIND, IMAGE_ENHANCE_KIND, IMAGE_BRAND_OVERLAY_KIND})" in operations
assert 'const isBrandOverlay = kind === "image_brand_overlay";' in PORTAL
assert "imageBrandOverlaySettings(item)" in history_cards
```

- [x] **Step 4: Run the focused tests and confirm RED**

Run:

```text
python -m pytest -q tests/test_copyfast_image_operations.py tests/test_operation_history_pagination.py tests/test_image_brand_overlay_contracts.py tests/test_image_operation_portal_contracts.py
```

Expected: failure because the current server and combined renderer intentionally omit Brand Overlay.

### Task 2: Implement the smallest reviewed allow-list and renderer change

**Files:**

- Modify: `copyfast_image_operations.py:59`
- Modify: `static/portal/portal.js:1602,5170,20107,20607`

- [x] **Step 1: Extend only the omitted-kind allow-list**

```python
IMAGE_HISTORY_KINDS = frozenset({IMAGE_RESIZE_KIND, IMAGE_ENHANCE_KIND, IMAGE_BRAND_OVERLAY_KIND})
```

Keep `SUPPORTED_KINDS`, owner filtering, bounded pagination, download routing, provider guards, and all per-kind history endpoints unchanged.

- [x] **Step 2: Make the combined portal renderer identify and render Brand Overlay using redacted public settings**

```javascript
const isBrandOverlay = kind === "image_brand_overlay";
const operationLabel = isResize
  ? `${resizeLabel} · ${String(item.preset || "custom")}`
  : isBrandOverlay
    ? "Brand Overlay Studio · deterministic"
    : (IMAGE_ENHANCE_PRESET_LABELS[preset] || preset);
const settings = isResize
  ? resizeLabel
  : isBrandOverlay
    ? imageBrandOverlaySettings(item)
    : imageEnhanceSettings(item);
```

Keep the dedicated renderer and its `IMAGE_BRAND_OVERLAY_HISTORY_KINDS` set intact. Do not surface raw overlay text, IDs, hashes, filenames, paths, URLs, wallet data, provider data or Bot records.

- [x] **Step 3: Update fixed copy and route notes from two Web-native kinds to the reviewed three-kind projection**

Use only clear Vietnamese copy, retaining the statement that Bot/provider output remains outside the route.

- [x] **Step 4: Re-run the focused tests and confirm GREEN**

Run the Task 1 command again. Expected: exit 0 with no failures.

### Task 3: Update the public migration contracts

**Files:**

- Modify: `docs/migration/IMAGE_HISTORY_WEB_NATIVE_CONTRACT.md`
- Modify: `docs/migration/IMAGE_BRAND_OVERLAY_CONTRACT.md`

- [x] **Step 1: Document the complete allow-list**

List `image_resize`, `image_enhance`, and `image_brand_overlay` as the sole combined Web-native image history kinds.

- [x] **Step 2: Preserve the dedicated Brand Overlay route boundary**

Document that `/image/brand-overlay` remains the task-specific authoring and filtered history surface even though its verified outputs also appear in `/image/history`.

- [x] **Step 3: Re-run the static contract tests**

```text
python -m pytest -q tests/test_image_brand_overlay_contracts.py tests/test_image_operation_portal_contracts.py
```

Expected: exit 0.

### Task 4: Verify, commit, and merge the sequential Web PR

**Files:**

- Verify only the files listed above plus generated migration evidence if the audit requires it.

- [x] **Step 1: Run the focused regression suite and diff gate**

```text
python -m pytest -q tests/test_copyfast_image_operations.py tests/test_operation_history_pagination.py tests/test_image_brand_overlay_contracts.py tests/test_image_operation_portal_contracts.py
python -m compileall -q copyfast_image_operations.py
git diff --check
```

- [x] **Step 2: Inspect the complete diff and protected comparators**

Confirm: no `bot.py`, payment/wallet, provider, Core Bridge, or deployment configuration changes; tests prove owner scoping, pagination, redaction and private download boundaries.

- [ ] **Step 3: Commit and open one PR**

```text
git add copyfast_image_operations.py static/portal/portal.js docs/migration/IMAGE_HISTORY_WEB_NATIVE_CONTRACT.md docs/migration/IMAGE_BRAND_OVERLAY_CONTRACT.md tests
git commit -m "Include Brand Overlay in Web image history"
git push -u origin feature/p0-webapp-image-history-unified
gh pr create --base main --head feature/p0-webapp-image-history-unified --title "Include Brand Overlay in Web image history"
```

- [ ] **Step 4: Wait for required CI, merge, then verify `main` equals `origin/main`**

No Railway deploy, provider call, PayOS action, Telegram live flow, wallet mutation, or `LIVE PASS` claim is part of this task.
