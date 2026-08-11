# Image Operation Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a customer explicitly export a verified private Image Operation PNG to Asset Vault and open one fresh local Image Operation form with only the newly server-returned, owner-scoped asset UUID selected.

**Architecture:** The existing server export endpoint remains the only producer of an Asset Vault receipt. A narrow client continuation helper accepts only a validated UUID and one fixed local target (`/image/edit`, `/image/resize`, `/image/background-cleanup`, or `/image/brand-overlay`), stores it only in page-memory, changes same-origin history, and rehydrates the target route. No source operation settings, bytes, URL, provider state, Bot state, quote, or job are transferred.

**Tech Stack:** FastAPI backend already in place; vanilla JavaScript Portal client; Python static contract tests.

---

### Task 1: Lock the continuation boundary with a failing contract test

**Files:**

- Modify: `tests/test_image_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Write the failing test**

```python
def test_verified_image_export_can_continue_only_with_a_fresh_active_asset_receipt() -> None:
    assert 'image-operation-export-to-continue' in PORTAL
    assert 'data-image-operation-continue-target' in PORTAL
    assert 'restoreImageOperationContinuation' in PORTAL
    action = _export_actions_source()
    assert 'const continueTarget = String(fields.__imageOperationContinueTarget || "").trim();' in action
    assert 'assetState !== "active"' in action
    assert 'restoreImageOperationContinuation(continueTarget, asset.id)' in action
    assert 'window.history.pushState({}, "", continueTarget)' in action
    for forbidden in ("provider", "bridge", "telegram", "bot", "wallet", "payment", "payos", "source_asset_id"):
        assert forbidden not in action.lower()
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python -m pytest -q tests/test_image_operation_asset_export_portal_contracts.py`

Expected: the new test fails because the continuation action and helper do not yet exist.

### Task 2: Add the minimum truthful continuation UI and client transition

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`

- [ ] **Step 1: Expose only finite continuation targets**

```javascript
const IMAGE_OPERATION_CONTINUATION_TARGETS = new Set([
  "/image/edit", "/image/resize", "/image/background-cleanup", "/image/brand-overlay"
]);

function restoreImageOperationContinuation(route, assetId) {
  const targetRoute = normalizePath(route || "");
  if (!IMAGE_OPERATION_CONTINUATION_TARGETS.has(targetRoute) || !validVaultAssetId(assetId)) return false;
  transientFormDrafts.set(targetRoute, { source_asset_id: assetId });
  return true;
}
```

- [ ] **Step 2: Add a confirmed per-route control**

```javascript
data-portal-action="image-operation-export-to-continue"
data-image-operation-continue-target="/image/edit"
data-portal-confirm="Lưu PNG đã được xác minh vào Asset Vault rồi mở một form chỉnh ảnh mới? Chỉ Asset UUID mới được chọn; thông số cũ không được chuyển."
```

The target must be selected from a constant by the originating local route. The control remains hidden unless the existing export capability and completed/download-ready conditions are true.

- [ ] **Step 3: Reuse the existing export receipt only**

```javascript
const preparingContinuation = action === "image-operation-export-to-continue";
const continueTarget = String(fields.__imageOperationContinueTarget || "").trim();
if (preparingContinuation && !IMAGE_OPERATION_CONTINUATION_TARGETS.has(continueTarget)) {
  throw new Error("Thao tác tiếp theo không thuộc Image Operations local đã được review.");
}
// After POST export and only when assetState === "active":
if (!window.TOANAASPortal.restoreImageOperationContinuation(continueTarget, asset.id)) {
  throw new Error("Máy chủ chưa trả Asset Vault ID hợp lệ để mở thao tác mới.");
}
window.history.pushState({}, "", continueTarget);
merge({ path: continueTarget, title: "TOAN AAS" });
await hydrate();
```

Do not add a browser upload, query-string asset ID, localStorage/sessionStorage, URL/path/bytes argument, or API endpoint.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run: `python -m pytest -q tests/test_image_operation_asset_export_portal_contracts.py`

Expected: PASS with zero failures.

### Task 3: Review and verify the slice

**Files:**

- Review: `static/portal/portal.js`
- Review: `static/portal/integration.js`
- Review: `tests/test_image_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Run surrounding safety tests**

Run: `python -m pytest -q tests/test_copyfast_image_operations.py tests/test_image_operation_portal_contracts.py tests/test_image_operation_asset_export.py tests/test_image_operation_asset_export_source_integrity.py tests/test_image_operation_asset_export_finalization.py tests/test_image_operation_asset_export_leases.py tests/test_image_operation_asset_export_endpoint_hardening.py tests/test_image_operation_asset_export_portal_contracts.py`

Expected: PASS with zero failures.

- [ ] **Step 2: Run syntax and diff checks**

Run: `node --check static/portal/portal.js`, `node --check static/portal/integration.js`, and `git diff --check`.

Expected: each command exits 0.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-08-11-image-operation-continuation.md static/portal/portal.js static/portal/integration.js tests/test_image_operation_asset_export_portal_contracts.py
git commit -m "Continue verified image outputs in web operations"
```
