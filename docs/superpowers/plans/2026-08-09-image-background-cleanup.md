# Image Background Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded, owner-scoped, verified Web-native utility that removes only a contiguous near-solid edge background and produces a private transparent PNG.

**Architecture:** Extend the existing Image Operations renderer and generic operation table with a fourth local kind, `image_background_cleanup`. The browser selects a signed-owner Asset Vault image and a closed cleanup profile; FastAPI validates/rehashes the input, Pillow performs an edge-connected flood-fill, and the existing private operation/download pipeline verifies the output. The generic Bot/Core Bridge `/image/remove-background` feature remains independent and guarded.

**Tech Stack:** FastAPI, Pydantic, SQLite, Pillow, vanilla Portal JavaScript/CSS, pytest.

---

## Task Contract

```text
TASK_ID=P0.WEBAPP.IMAGE_BACKGROUND_CLEANUP
GOAL=Deliver an actual local plain-background cleanup utility without claiming AI/provider removal.
SCOPE=copyfast_image_operations.py, copyfast_db.py, copyfast_api.py, static/portal/portal.js, static/portal/integration.js, tests, migration docs/reports.
ALLOWED_FILES=The scope files and a new plan/contract/test only.
PROTECTED_FILES=bot.py, bridge credential/configuration, wallet/PayOS/webhook logic, provider clients, existing resize/enhance/brand-overlay behavior.
ACCEPTANCE=Private owner-scoped PNG only; no-match/source/tamper cases fail closed; UI never claims AI/provider output; raw imgtool callbacks remain fail-closed.
TARGETED_TESTS=tests/test_copyfast_image_operations.py plus a new portal contract test.
REGRESSION_TESTS=tests/test_image_operation_portal_contracts.py, tests/test_migration_audit.py.
PROTECTED_COMPARATORS=Existing 19 Image Operations tests; no diff in bot.py/bridge/payment files; provider-call count remains zero.
PROHIBITED_ACTIONS=Deploy, change ENV/credentials, call Bot/provider, mutate wallet/payment, execute webhooks, delete project/user data.
STOP_CONDITIONS=Dirty shared worktree, bridge/payment/provider change required, unsupported source/output validation, or a baseline regression.
BASE_SHA=477ad234b7b04859f459dd99c5f45cf0568f42b4
```

### Task 1: Establish the red backend contract

**Files:**

- Modify: `tests/test_copyfast_image_operations.py`

- [ ] **Step 1: Add a helper and one failing end-to-end test**

```python
def plain_background_image_bytes() -> bytes:
    image = Image.new("RGB", (96, 96), (248, 248, 248))
    for y in range(28, 70):
        for x in range(30, 66):
            image.putpixel((x, y), (18, 118, 198))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def background_cleanup(client, csrf, *, asset_id: str, key: str, profile: str = "white_studio"):
    return client.post(
        "/api/v1/image-operations/background-cleanup",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "profile": profile, "idempotency_key": key},
    )


def test_background_cleanup_is_private_idempotent_and_verifies_transparent_png(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "cleanup-owner@example.com")
        source = upload_image(client, csrf, key="cleanup-source-0001", body=plain_background_image_bytes(), name="product.png", content_type="image/png")
        created = background_cleanup(client, csrf, asset_id=source["id"], key="cleanup-create-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]
        assert operation["kind"] == "image_background_cleanup"
        assert operation["state"] == "completed"
        image = output_image(client, operation["id"])
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((48, 48))[3] == 255
        replay = background_cleanup(client, csrf, asset_id=source["id"], key="cleanup-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
```

- [ ] **Step 2: Run the test and confirm it fails because the route is absent**

Run: `python -m pytest -q tests/test_copyfast_image_operations.py -k background_cleanup`

Expected: one failure with HTTP 404 or an assertion that `image_background_cleanup` is missing; no unrelated baseline failure.

### Task 2: Implement the bounded backend operation

**Files:**

- Modify: `copyfast_db.py`
- Modify: `copyfast_api.py`
- Modify: `copyfast_image_operations.py`

- [ ] **Step 1: Add a closed feature gate and capability projection**

```python
def image_background_cleanup_enabled() -> bool:
    return os.environ.get("WEBAPP_IMAGE_BACKGROUND_CLEANUP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
```

Expose it as `image_background_cleanup_enabled` in the signed status payload only. It must not set `WEBAPP_PROVIDER_CALLS_ENABLED`, `WEBAPP_COPYFAST_ENABLED`, bridge readiness or any payment capability.

- [ ] **Step 2: Add the route schema and closed profile normalization**

```python
IMAGE_BACKGROUND_CLEANUP_KIND = "image_background_cleanup"
BACKGROUND_CLEANUP_PROFILES = {
    "white_studio": {"anchor": (250, 250, 250), "tolerance": 28},
    "light_neutral": {"anchor": (232, 232, 232), "tolerance": 34},
    "dark_neutral": {"anchor": (34, 34, 34), "tolerance": 30},
}


class ImageBackgroundCleanupRequest(BaseModel):
    source_asset_id: str = Field(min_length=36, max_length=36)
    profile: str = Field(default="white_studio", min_length=3, max_length=32)
    idempotency_key: str = Field(min_length=12, max_length=160)
```

Validate the UUID/key with the existing helpers. Normalize profile only to the exact closed map. Do not accept browser RGB values, masks, alpha thresholds, dimensions, paths, URLs, bytes, provider IDs or callback text.

- [ ] **Step 3: Implement edge-connected cleanup and strict output validation**

```python
def _cleanup_background(image, *, anchor: tuple[int, int, int], tolerance: int, Image):
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    queue = deque(_edge_coordinates(width, height))
    visited = set(queue)
    removed = 0
    while queue:
        x, y = queue.popleft()
        red, green, blue, alpha = pixels[x, y]
        if alpha == 0 or max(abs(red-anchor[0]), abs(green-anchor[1]), abs(blue-anchor[2])) > tolerance:
            continue
        pixels[x, y] = (red, green, blue, 0)
        removed += 1
        for next_x, next_y in _orthogonal_neighbors(x, y, width, height):
            if (next_x, next_y) not in visited:
                visited.add((next_x, next_y))
                queue.append((next_x, next_y))
    if removed == 0:
        raise ImageOperationError("Không tìm thấy nền màu trơn phù hợp ở mép ảnh", code="IMAGE_BACKGROUND_NOT_DETECTED")
    return rgba, removed
```

Use a bounded `deque`, source geometry checks and the existing isolated staging/output helpers. Record only the profile and removed pixel count in the operation settings/audit detail. Verify that the encoded output parses as PNG/RGBA, matches the source geometry, has non-zero transparent pixels and passes existing SHA/storage validation. Never label it `AI`, `RemoveBG`, `Cutout`, or `provider`.

- [ ] **Step 4: Wire history, read model and private download to the new explicit kind**

Add the kind only to explicitly reviewed `SUPPORTED_KINDS`, `IMAGE_HISTORY_KINDS`, operation projection labels and history selectors. Keep the generic feature bridge denylist such that `/api/v1/features/image_remove_background/*` cannot enter this local endpoint. Reuse owner checks and the existing `download_image_operation` path.

- [ ] **Step 5: Run the focused backend test and confirm it passes**

Run: `python -m pytest -q tests/test_copyfast_image_operations.py -k background_cleanup`

Expected: `1 passed`.

### Task 3: Cover failure and protected-boundary cases

**Files:**

- Modify: `tests/test_copyfast_image_operations.py`

- [ ] **Step 1: Add negative and ownership tests before extending production code**

```python
def test_background_cleanup_rejects_unknown_profile_no_match_cross_owner_and_disabled_gate(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "cleanup-boundary@example.com")
        source = upload_image(client, csrf, key="cleanup-boundary-source-0001", body=image_bytes("PNG"), name="source.png", content_type="image/png")
        assert background_cleanup(client, csrf, asset_id=source["id"], key="cleanup-profile-0001", profile="provider").status_code == 422
        no_match = background_cleanup(client, csrf, asset_id=source["id"], key="cleanup-no-match-0001")
        assert no_match.status_code == 422
```

Extend the test with a second signed account (expect 404/403 with no output row), same-key changed profile conflict, output storage tamper (download fails closed), and disabled `WEBAPP_IMAGE_BACKGROUND_CLEANUP_ENABLED=false` (503/no row).

- [ ] **Step 2: Run the focused test file after every failing assertion is made green**

Run: `python -m pytest -q tests/test_copyfast_image_operations.py`

Expected: existing 19 baseline tests plus the new cleanup tests pass with zero failures.

### Task 4: Add the professional private Web workspace

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Create: `tests/test_image_background_cleanup_portal_contracts.py`

- [ ] **Step 1: Write a failing portal contract test**

```python
def test_background_cleanup_portal_is_owner_scoped_and_never_claims_ai_or_provider_execution() -> None:
    assert 'customerPage("/image/background-cleanup", "Xóa nền màu trơn"' in PORTAL
    assert 'data-portal-action="image-operation-background-cleanup"' in PORTAL
    assert 'api("/image-operations/background-cleanup", {' in INTEGRATION
    assert 'source_asset_id' in INTEGRATION
    assert 'provider' not in cleanup_action.lower()
    assert 'removebg' not in cleanup_action.lower()
    assert 'wallet' not in cleanup_action.lower()
```

The test must also assert CSRF, idempotency, no browser file bytes/path/URL, explicit no-match failure copy, private history/download, and that `/image/remove-background` remains a distinct guarded canonical bridge feature.

- [ ] **Step 2: Run the new test and confirm red**

Run: `python -m pytest -q tests/test_image_background_cleanup_portal_contracts.py`

Expected: failure because the route/layout/action does not yet exist.

- [ ] **Step 3: Implement the route, bounded controls and hydration**

```javascript
customerPage("/image/background-cleanup", "Xóa nền màu trơn", "Làm trong suốt phần nền liên thông từ mép ảnh; không phải AI cắt chủ thể.", ICONS.image, {
  layout: "image-background-cleanup", type: "image-operation", action: "none", status: "guarded", fields: []
});
```

Render a signed-account Asset Vault selector and a three-value profile select. Submit only `{ source_asset_id, profile, idempotency_key }` through the existing CSRF API helper. Hydrate only explicit `image_background_cleanup` history rows. Add stale-response/session/path guards matching resize/enhance; clear old private data when ownership/session changes. A disabled capability shows guarded state. A no-match response explains that the tool handles plain edge-connected backgrounds and does not emit a fallback image.

- [ ] **Step 4: Run the portal contract test and confirm green**

Run: `python -m pytest -q tests/test_image_background_cleanup_portal_contracts.py`

Expected: all portal assertions pass.

### Task 5: Preserve parity and document the truth boundary

**Files:**

- Create: `docs/migration/IMAGE_BACKGROUND_CLEANUP_WEB_NATIVE_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `tests/test_migration_audit.py` only if the audit needs an explicit assertion that raw `imgtool|*` remains fail-closed.

- [ ] **Step 1: Document the independent authority boundary**

Document source ownership, profiles, no-match failure, explicit private delivery checks and the facts that this is not Bot RemoveBG/Cutout, a provider call, wallet/payment action or a raw `imgtool` callback adapter. Do not add raw Bot callback values to the browser manifest.

- [ ] **Step 2: Run parity safeguards**

Run: `python -m pytest -q tests/test_migration_audit.py -k imgtool`

Expected: all selected tests pass; no raw `imgtool` action gains a generic Web route.

### Task 6: Review, verify and integrate

**Files:**

- Review all task files only.

- [ ] **Step 1: Inspect the complete diff and protected files**

Run:

```powershell
git diff --check
git diff --name-only 477ad234b7b04859f459dd99c5f45cf0568f42b4...HEAD
git diff -- bot.py copyfast_bridge.py billing.py
```

Expected: no whitespace error; no `bot.py`, bridge, billing, wallet, PayOS or webhook diff.

- [ ] **Step 2: Run proportionate verification**

Run:

```powershell
python -m pytest -q tests/test_copyfast_image_operations.py tests/test_image_operation_portal_contracts.py tests/test_image_background_cleanup_portal_contracts.py
python -m pytest -q tests/test_migration_audit.py -k imgtool
python -m py_compile copyfast_image_operations.py copyfast_db.py copyfast_api.py
node --check static/portal/portal.js
node --check static/portal/integration.js
git diff --check
```

Expected: all selected tests and syntax checks exit 0.

- [ ] **Step 3: Regenerate migration evidence only if audit inputs or contract mappings changed**

Run the repository's existing static-only `scripts/migration/audit_bot_to_web.py` command with the frozen Bot SHA and no provider/Bot import. Inspect the generated JSON for secret redaction and confirm no raw `imgtool` callback became browser execution.

- [ ] **Step 4: Commit, push, create PR, inspect CI, merge and fast-forward main**

Use one focused commit message: `Add Web-native plain background cleanup`. Merge only after focused CI checks are green, then fast-forward `D:\TOANAAS\TOAN_AAS_WEB_APP\GitHub` to the merge SHA. Do not deploy Railway or claim live behavior.
