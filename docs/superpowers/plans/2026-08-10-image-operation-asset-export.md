# Superseded — Image Operation Asset Export Implementation Plan

> Do not execute this initial plan. Use
> [the fenced implementation plan](2026-08-10-image-operation-asset-export-fenced.md),
> reviewed for lease fencing, quota reservation, lifecycle-truthful replay and
> descriptor-safe copying.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a signed Web owner explicitly save a verified local Image Operation PNG into an independent private Asset Vault record without expanding Bot/provider/payment authority.

**Architecture:** Add one owner-scoped export relation and a server-only Asset Vault persistence helper. The Image Operations endpoint verifies its own completed PNG through a pinned descriptor, then asks the Asset Vault helper to copy, rehash, validate, atomically promote, quota-check and persist a fresh private object. The Portal merely confirms and calls the same-origin API with an opaque operation ID and an idempotency key.

**Tech Stack:** Python 3.12, FastAPI, SQLite, private filesystem storage, existing Portal JavaScript, pytest.

---

### Task 1: Add failing export-boundary tests

**Files:**

- Create: `tests/test_image_operation_asset_export.py`
- Create: `tests/test_image_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Write focused API tests before implementation**

Create `tests/test_image_operation_asset_export.py` by reusing the existing
isolated image-operation client fixture pattern. Include these independent
tests:

```python
def export_operation(client: TestClient, csrf: str, operation_id: str, key: str):
    return client.post(
        f"/api/v1/image-operations/{operation_id}/export-to-asset-vault",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
    )


def test_completed_allowed_png_exports_once_to_an_independent_asset_vault(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, image_operation_export_enabled=True) as client:
        csrf = register_and_login(client, "export-owner@example.com")
        source = upload_image(client, csrf, key="export-source-0001", body=image_bytes("PNG"), name="source.png", content_type="image/png")
        operation = resize(client, csrf, asset_id=source["id"], key="export-operation-0001").json()["data"]["operation"]
        response = export_operation(client, csrf, operation["id"], "export-copy-0001")
        assert response.status_code == 200
        asset = response.json()["data"]["asset"]
        assert asset["state"] == "active"
        assert asset["content_type"] == "image/png"
        assert client.get(f"/api/v1/asset-vault/{asset['id']}/download").content == client.get(f"/api/v1/image-operations/{operation['id']}/download").content


def test_export_rejects_disabled_anonymous_foreign_incomplete_unknown_and_tampered_outputs(tmp_path, monkeypatch):
    # Use one completed resize and assert each denial leaves
    # SELECT COUNT(*) FROM web_asset_files unchanged. Cover no CSRF, a second
    # owner, disabled export flag, state='processing', kind='unreviewed', and a
    # modified output file. Assert every public body omits storage_key, sha256,
    # path, provider, bot, wallet and payment keys.
    assert {"disabled", "anonymous", "foreign", "incomplete", "unknown", "tampered"} == {
        "disabled", "anonymous", "foreign", "incomplete", "unknown", "tampered"
    }


def test_export_is_idempotent_quota_bound_and_lifecycle_independent(tmp_path, monkeypatch):
    # Replay one key and assert the same asset id. Send a second valid key for
    # the same operation and assert it returns that same id without increasing
    # web_asset_files count. Set the tenant quota below output bytes and assert
    # no Asset Vault row is added. Archive/restore the exported asset through
    # its existing lifecycle API and assert the Image Operation stays completed.
    assert "image_operation_asset_export" == "image_operation_asset_export"
```

Use real PNG bytes and the existing TestClient; mock neither storage nor
provider. Set all three local flags only in test process environment. Verify
the database mapping and audit detail contain no filename, path or digest.

- [ ] **Step 2: Write static Portal/API safety tests**

Create `tests/test_image_operation_asset_export_portal_contracts.py` to assert:

```python
assert 'data-portal-action="image-operation-export-to-asset-vault"' in PORTAL
assert '"image-operation-export-to-asset-vault": Boolean(account && me.csrf_token' in INTEGRATION
assert 'api(`/image-operations/${encodeURIComponent(operationId)}/export-to-asset-vault`' in INTEGRATION
assert "provider" not in export_action_source.lower()
assert "bridge" not in export_action_source.lower()
assert "wallet" not in export_action_source.lower()
assert "payos" not in export_action_source.lower()
assert "fetch(" not in export_action_source
assert "/image-operations/" not in SERVICE_WORKER or "private" in SERVICE_WORKER.lower()
```

Also assert `app.py` assigns the exact POST route to a fixed pre-session
rate-limit bucket and that the endpoint uses `require_csrf`.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_image_operation_asset_export.py tests/test_image_operation_asset_export_portal_contracts.py
```

Expected: failure because the export endpoint/capability/relation do not yet
exist. The failing assertions must not be caused by a missing test fixture,
provider, Bot, Railway or production environment.

### Task 2: Add the server-only export relation and persistence boundary

**Files:**

- Modify: `copyfast_db.py`
- Modify: `copyfast_assets.py`
- Modify: `copyfast_image_operations.py`
- Modify: `copyfast_api.py`
- Modify: `app.py`

- [ ] **Step 1: Add an additive schema and closed enablement function**

Add `image_operation_asset_export_enabled()` in `copyfast_db.py`, returning
true only for `WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED` values in
`{"1", "true", "yes", "on"}`. Add an additive
`web_image_operation_asset_exports` table with one `operation_id` primary key,
`account_id`, nullable `asset_id`, `state`, `request_fingerprint`,
`created_at`, `updated_at`, foreign keys, and indexes for owner/state reads.
Do not alter/drop existing image-operation or Asset Vault columns.

- [ ] **Step 2: Add a server-only Asset Vault stream-copy helper**

Implement one exported helper in `copyfast_assets.py` that accepts a trusted,
already-pinned binary stream and server-derived metadata only. It must:

```python
def export_verified_image_operation_output(
    *,
    account_id: str,
    operation_id: str,
    kind: str,
    project_id: str | None,
    stream: BinaryIO,
    expected_bytes: int,
    expected_digest: str,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """Copy one trusted PNG into a fresh private Asset Vault record."""
    return _persist_image_operation_export(
        account_id=account_id,
        operation_id=operation_id,
        kind=kind,
        project_id=project_id,
        stream=stream,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
```

The helper copies chunks into Vault staging, rehashes and PNG-signature
validates the bytes, uses a fresh `objects/<random>.blob` key, checks quota
inside the completion transaction, inserts a new `web_asset_files` row,
finishes the one-export relation and records a redacted audit event. It must
clean staging/final files and pending reservation on error; a stale pending
reservation is reclaimed without moving an old output.

- [ ] **Step 3: Add the narrow Image Operations endpoint**

Implement:

```python
@router.post("/{operation_id}/export-to-asset-vault")
async def export_image_operation_to_asset_vault(
    operation_id: str,
    request: Request,
    idempotency_key: str | None = Header(alias="Idempotency-Key"),
    account: dict = Depends(require_csrf),
):
    _require_asset_export_enabled()
    operation_id = _uuid(operation_id, label="Mã thao tác ảnh")
    return _export_completed_png_for_owner(
        operation_id=operation_id,
        account_id=str(account["id"]),
        request_id=_request_id(request),
        idempotency_key=_idempotency_key(idempotency_key),
    )
```

Before calling the helper, enforce the three local flags, UUID/account owner,
the four-item kind allowlist, completed state, canonical PNG metadata and the
existing pinned output verifier. Pass no browser data besides the header key.
If the output fails re-validation, mark the Image Operation unavailable using
its existing path and return a sanitized guarded response. Add the public
boolean `image_operation_export_enabled` in `copyfast_api._flags()` only as a
safe effective flag; it grants no route authority itself.

- [ ] **Step 4: Add an early route-specific rate limit**

In `app.py`, add a precise POST predicate for
`/api/v1/image-operations/{uuid}/export-to-asset-vault`, separate it from
decoder/render buckets, give it a bounded fixed rate, and include it in
rate-limit error classification. Do not broaden an existing prefix match to
other future Image Operations routes.

- [ ] **Step 5: Run the API suite and verify GREEN**

Run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_image_operation_asset_export.py tests/test_copyfast_image_operations.py tests/test_copyfast_assets.py tests/test_asset_vault_lifecycle.py
```

Expected: exit 0. Any failure in digest, owner, quota, idempotency or
lifecycle behavior is fixed in production code, not weakened in tests.

### Task 3: Connect the explicit Portal interaction

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal-i18n.js` only if a new fixed string must be
  localized through the existing shared key model
- Modify: `static/portal/portal.css` only if current button/action-row classes
  cannot represent the second action without an alignment regression

- [ ] **Step 1: Render a constrained secondary action on valid completed cards**

Create a small shared renderer for the four permitted operation card families.
It renders `Lưu vào Asset Vault` only for a valid UUID, completed state,
`download_ready === true`, and the server-published export capability. Attach
only the opaque operation ID, the current route and a truthful confirmation
message. Do not attach a filename, path, hash, URL, blob, asset ID, project
ID, raw output, provider option or Bot data.

- [ ] **Step 2: Add the same-origin action handler**

Add a handler branch that validates the current route and UUID, acquires a
single in-memory submission key, calls only:

```javascript
api(`/image-operations/${encodeURIComponent(operationId)}/export-to-asset-vault`, {
  method: "POST",
  headers: { "Idempotency-Key": submission.key }
})
```

Validate the returned safe Asset Vault receipt, refresh the relevant image
operation listing plus Asset Vault, then show a sanitized success message. No
browser byte read, `fetch`, provider, bridge, wallet, PayOS or Bot call is
allowed. Failed/disabled responses retain the operation's existing truthful
state and create no local substitute.

- [ ] **Step 3: Run Portal contracts and syntax checks**

Run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_image_operation_asset_export_portal_contracts.py tests/test_image_operation_portal_contracts.py tests/test_image_enhance_portal_contracts.py tests/test_image_background_cleanup_portal_contracts.py tests/test_image_brand_overlay_contracts.py tests/test_portal_safety_contracts.py
node --check static/portal/portal.js
node --check static/portal/integration.js
```

Expected: exit 0; all private work remains excluded from PWA cache and no
non-local authority appears in the action slice.

### Task 4: Document the contract and refresh migration evidence

**Files:**

- Create: `docs/migration/IMAGE_OPERATION_ASSET_EXPORT_CONTRACT.md`
- Modify: `docs/migration/ASSET_VAULT_CONTRACT.md`
- Modify: `docs/migration/WEB_NATIVE_OUTPUT_LINEAGE_CONTRACT.md`
- Modify: `docs/migration/ENV_AND_PROVIDER_MAP.md`
- Modify: `README.md`
- Modify: generated `docs/migration/*` and `reports/migration/*.json`

- [ ] **Step 1: Record authority, storage and non-goal boundaries**

Document the exact route, four-kind allowlist, no-browser-byte policy,
pin/copy/re-hash transaction, one-export relation, quota/idempotency,
archive/restore independence, no-store/PWA boundary, disabled-by-default flag,
and explicit exclusions of Bot/provider/wallet/PayOS/job/public delivery.

- [ ] **Step 2: Refresh static migration evidence after source commit**

Commit all source and tests first, then run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --web-root . --report-dir reports/migration --docs-dir docs/migration --web-revision <source-commit-sha>
```

Update `docs/migration/TEST_EVIDENCE.md` to the generated Web route count if
needed. The audit is static only and must not import/start Bot, contact a
provider, call PayOS or mutate wallet state.

- [ ] **Step 3: Commit contract/evidence changes separately**

```powershell
git add README.md docs/migration reports/migration docs/superpowers/specs/2026-08-10-image-operation-asset-export-design.md docs/superpowers/plans/2026-08-10-image-operation-asset-export.md
git commit -m "Document image operation asset export boundary"
```

### Task 5: Final review, verification and PR

**Files:**

- No intended source edits.

- [ ] **Step 1: Verify migration evidence against final HEAD**

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/migration/audit_bot_to_web.py --verify-web-evidence --web-root . --report-dir reports/migration --docs-dir docs/migration --web-revision <final-head-sha>
```

- [ ] **Step 2: Run proportionate regression and static checks**

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_image_operation_asset_export.py tests/test_image_operation_asset_export_portal_contracts.py tests/test_copyfast_image_operations.py tests/test_copyfast_assets.py tests/test_asset_vault_lifecycle.py tests/test_image_operation_portal_contracts.py tests/test_image_enhance_portal_contracts.py tests/test_image_background_cleanup_portal_contracts.py tests/test_image_brand_overlay_contracts.py tests/test_portal_safety_contracts.py
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile copyfast_db.py copyfast_assets.py copyfast_image_operations.py copyfast_api.py app.py
node --check static/portal/portal.js
node --check static/portal/integration.js
git diff --check
```

- [ ] **Step 3: Perform review and handoff**

Compare the complete branch diff to `origin/main`, rerun the declared
protected comparators, and request a focused security review for the
filesystem/ownership/idempotency path. Push only this feature branch and open
one PR. Do not deploy Railway, alter ENV, invoke providers, mutate wallet or
claim `LIVE PASS`.
