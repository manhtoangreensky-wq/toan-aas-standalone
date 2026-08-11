# Audio Asset Operation Asset Vault Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export a verified completed Web-native Audio Asset Operation MP3/M4A output into the signed owner's private Asset Vault without introducing Bot, provider, wallet, payment, or external delivery behavior.

**Architecture:** Audio Operations remain the authoritative output store until an owner explicitly requests export. A separate Audio export relation and idempotency map reserve one Vault object, reverify and copy a server-opened output into Vault staging, then publish an independent active Vault row. The Portal only requests this existing same-origin boundary and refreshes server truth.

**Tech Stack:** FastAPI, SQLite schema helpers, private filesystem staging/hash verification, vanilla Portal JavaScript, pytest static/HTTP contracts, Node syntax checks.

---

### Task 1: Establish failing Audio export contracts

**Files:**

- Create: `tests/test_audio_operation_asset_export.py`
- Modify: `tests/test_audio_asset_operations_portal_contracts.py`

- [ ] **Step 1: Add server RED tests for an explicit protected export**

Create a client fixture with isolated Asset Vault and Audio Operations roots,
then assert `POST /api/v1/audio-asset-operations/{operation_id}/export-to-asset-vault`
requires the export flag, signed account, CSRF, and `Idempotency-Key`.

```python
response = client.post(
    f"/api/v1/audio-asset-operations/{operation_id}/export-to-asset-vault",
    headers={"X-CSRF-Token": csrf, "Idempotency-Key": "audio-export-copy-0001"},
)
assert response.status_code == 200
assert response.json()["data"]["asset"]["state"] == "active"
```

- [ ] **Step 2: Add lifecycle and replay RED cases**

Cover one completed MP3 and one completed M4A transform, same-key replay,
different-operation key collision, foreign operation invisibility, inspect-only
operation rejection, unavailable/corrupt output, stale lease, and one Asset
Vault row after repeated requests.

- [ ] **Step 3: Add Portal RED contracts**

Require the export control only for completed download-ready transform outputs,
the `audio-asset-operation-export-to-asset-vault` capability, an opaque
operation UUID field, same-origin export path, `Idempotency-Key`, refresh of
Audio Operations plus Asset Vault, and no provider/Bot/wallet/payment/PayOS or
Content Handoff write literal in the action branch.

- [ ] **Step 4: Run RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_audio_operation_asset_export.py tests/test_audio_asset_operations_portal_contracts.py
```

Expected: the new export assertions fail because no Audio export flag, route,
schema relation, or Portal action exists.

### Task 2: Add isolated export persistence and private finalization

**Files:**

- Modify: `copyfast_db.py`
- Modify: `copyfast_assets.py`
- Test: `tests/test_audio_operation_asset_export.py`

- [ ] **Step 1: Add the closed feature flag and schema**

Add `audio_asset_operation_export_enabled()` with default `false`. Add
`web_audio_asset_operation_asset_exports` and
`web_audio_asset_operation_asset_export_requests` using the existing Image
export relation shape: one operation/owner relation, copying/completed state,
lease generation/token/expiry, reserved byte count, pending Vault storage key,
and request-fingerprint/idempotency constraints. Add account/state/expiry and
request-operation indexes.

- [ ] **Step 2: Add Audio-specific reservation, lease and receipt helpers**

In `copyfast_assets.py`, define Audio-specific source/reservation/lease/final
receipt dataclasses and helpers mirroring the fenced Image export lifecycle.
The helpers must accept only a server-opened source stream plus closed
MP3/M4A metadata, reserve quota before bytes are copied, reject stale leases,
and return only an Asset Vault public projection.

- [ ] **Step 3: Copy and verify before publishing**

Implement the finalizer with Vault staging, `O_NOFOLLOW`/safe-path behavior
already used by the Asset Vault, bounded byte count, SHA-256 equality, fixed
format/content-type/extension validation, atomic publication, and transactional
creation of one active `web_asset_files` row. On any failure, release the live
lease or mark only the current relation safely; never remove another attempt's
object.

- [ ] **Step 4: Run focused GREEN persistence tests**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_audio_operation_asset_export.py
```

Expected: every new lifecycle/security case passes without a real FFmpeg,
provider, Bot, or payment call.

### Task 3: Expose one Audio Operations export route

**Files:**

- Modify: `copyfast_audio_asset_operations.py`
- Modify: `copyfast_api.py`
- Modify: `app.py`
- Test: `tests/test_audio_operation_asset_export.py`

- [ ] **Step 1: Add the server-only output descriptor**

Build an Audio export source only from the owner-scoped operation row after
checking `audio_convert`/`audio_normalize`, `completed`, canonical
`output_available`, expected MP3/M4A storage key, byte count, SHA-256 and
probe metadata. Open the private output server-side; do not accept a browser
path, filename, hash, format or bytes.

- [ ] **Step 2: Add the explicit POST before download**

Implement the route with `Depends(require_csrf)`, `Idempotency-Key`,
default-off Audio export flag plus Asset Vault/Audio Operations gates, current
owner checks, narrow post rate limit, the reservation/finalizer, and a
truthful `completed`, `processing`, `guarded`, or `unavailable` envelope.

- [ ] **Step 3: Preserve protected behavior**

Leave `download_audio_asset_operation`, Audio Operation creation, source
selection, FFmpeg argv, provider boundaries, wallet/payment paths and service
worker policy unchanged. Extend the server bootstrap capability only as a
boolean that requires a signed CSRF account and all three relevant feature
flags.

- [ ] **Step 4: Run server regression checks**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_audio_operation_asset_export.py tests/test_copyfast_audio_asset_operations.py
```

Expected: Audio export passes while existing Audio Operation behavior remains
unchanged.

### Task 4: Add the explicit Portal action

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Modify: `tests/test_audio_asset_operations_portal_contracts.py`

- [ ] **Step 1: Render the opt-in control**

Place **Lưu vào Asset Vault** beside **Tải private** only when the operation
is a completed transform with verified output and the new capability is true.
Use only `data-audio-asset-operation-id`, route and a Vietnamese confirmation.

- [ ] **Step 2: Handle the action behind a submission fence**

Use scope `audio-asset-operation-export:${operationId}`, validate the opaque
UUID and current `/audio/assets` route, call only
`/audio-asset-operations/${encodeURIComponent(operationId)}/export-to-asset-vault`
with `Idempotency-Key`, validate the completed active receipt, then refresh
Audio Operations and Asset Vault. Nonterminal/guarded/unavailable receipts
stay truthful and never synthesize an asset.

- [ ] **Step 3: Carry only the operation ID from the DOM**

Extend Portal action field extraction for the exact export action without
altering generic audio reference pagination or download fields.

- [ ] **Step 4: Preserve the bounded audio projection through bootstrap**

Extend `normalizeBootstrap()` with the owner-scoped Audio Operations
projection, its read states, and the new default-off export flag. Do not add
raw media, path, hash, source Asset Vault ID, provider, Bot, wallet/payment,
PayOS, or Content Handoff fields.

- [ ] **Step 5: Run Portal GREEN checks**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_audio_asset_operations_portal_contracts.py tests/test_audio_operation_asset_export.py tests/test_image_operation_asset_export_portal_contracts.py tests/test_document_operation_asset_export_portal_contracts.py
node --check static/portal/portal.js
node --check static/portal/integration.js
git diff --check
```

Expected: Audio export is explicit and bounded; Document/Image export and
Content Handoff behavior continue to pass.

### Task 5: Review, evidence and integration

**Files:**

- Create: `docs/migration/AUDIO_OPERATION_ASSET_EXPORT_CONTRACT.md`
- Create: `docs/superpowers/specs/2026-08-11-audio-operation-asset-export-design.md`
- Create: `docs/superpowers/plans/2026-08-11-audio-operation-asset-export.md`
- Modify: `docs/migration/README.md`
- Modify: `reports/migration/preflight.json`
- Modify: `reports/migration/web_inventory.json`

- [ ] **Step 1: Review protected domains**

Confirm no diff in `bot.py`, bridge code, wallet/payment/PayOS modules,
provider adapters, service worker, production ENV files, or unrelated media
operations.

- [ ] **Step 2: Request independent reviews**

First review spec compliance for explicit opt-in, active-owner receipt,
idempotency and safe output copying. Then review code quality for staging
cleanup, lease ownership, source integrity and Portal event handling.

- [ ] **Step 3: Regenerate static evidence after the feature commit**

Run `scripts/migration/audit_bot_to_web.py` against frozen Bot SHA
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`, with `TEMP`/`TMP` outside the
repository. Verify the resulting evidence against the feature/evidence commit
using `--verify-web-evidence`.

- [ ] **Step 4: Commit and integrate in order**

Commit feature code as `Export verified audio operations to Asset Vault`,
commit evidence separately, push the branch, create a PR, wait for green CI,
and merge only after PR state is clean. Do not deploy Railway.
