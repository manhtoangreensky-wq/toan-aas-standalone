# Document Operation Asset Vault Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save completed, verified Web-native Document Operation PDF/DOCX/TXT artifacts into the signed owner's private Asset Vault through a fenced server-side copy.

**Architecture:** Document Operations authenticates and opens the sealed source output. Asset Vault owns a separate document-export lease, copies into a new private object, revalidates the final artifact and commits the Vault asset only while the lease is current. The portal sends only an operation UUID in the path and an idempotency header.

**Tech Stack:** FastAPI, SQLite, Python standard library/PyPDF/OOXML validation already present in the repository, vanilla portal JavaScript, pytest.

---

### Task 1: Lock the document export boundary with RED tests

**Files:**

- Create: `tests/test_document_operation_asset_export.py`
- Create: `tests/test_document_operation_asset_export_portal_contracts.py`
- Modify: `tests/test_copyfast_document_operations.py`

- [ ] **Step 1: Add a real completed PDF export test**

Create a PDF through the existing private `pdf-split` helper, then exercise
the new route with only a CSRF token and idempotency header:

```python
created = client.post(
    f"/api/v1/document-operations/{operation_id}/export-to-asset-vault",
    headers={"X-CSRF-Token": csrf, "Idempotency-Key": "doc-export-pdf-0001"},
)
assert created.status_code == 200
asset = created.json()["data"]["asset"]
assert asset["extension"] == ".pdf"
assert asset["content_type"] == "application/pdf"
assert "storage_key" not in asset and "sha256" not in asset
```

Assert a replay returns the same Asset Vault ID and does not create another
row. Assert the source Document Operation remains downloadable and unchanged.

- [ ] **Step 2: Add controlled verified DOCX/TXT fixtures**

Use existing document-output builders or a test-only private operation fixture
that writes a valid, hash-matched OOXML/TXT artifact through repository
helpers. Assert `pdf_to_word_text` exports `.docx` and `image_ocr` exports
UTF-8 `.txt`. Do not mock a successful Asset Vault finalization.

- [ ] **Step 3: Add negative lease and ownership cases**

Write tests for another account, a non-completed record, `pdf_to_images`,
changed idempotency binding, missing/tampered source, stale lease and a
destination validation failure. Each case must assert no additional Vault row,
no completed receipt and no fake successful output.

- [ ] **Step 4: Run the new tests and observe RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_document_operation_asset_export.py tests/test_document_operation_asset_export_portal_contracts.py
```

Expected: the route/action is absent or the export contract fails, while the
existing Document Operations baseline remains unchanged.

### Task 2: Add closed feature/readiness and non-destructive lease storage

**Files:**

- Modify: `copyfast_db.py`
- Modify: `copyfast_api.py`
- Modify: `app.py`

- [ ] **Step 1: Add the default-closed capability**

Define `document_operation_export_enabled()` beside existing operation flags:

```python
def document_operation_export_enabled() -> bool:
    return _enabled("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", False)
```

Expose only the effective conjunction in the signed status payload:

```python
"document_operation_export_enabled": (
    enabled("WEBAPP_ASSET_VAULT_ENABLED", False)
    and enabled("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", False)
    and enabled("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", False)
),
```

Do not change actual ENV values, provider readiness, bridge readiness,
wallet/payment flags or feature pricing.

- [ ] **Step 2: Add document-specific export tables and indexes**

Inside the existing schema bootstrap, add `CREATE TABLE IF NOT EXISTS` for
`web_document_operation_asset_exports` and
`web_document_operation_asset_export_requests`. The relation stores
`operation_id`, `account_id`, `asset_id`, `state`, `request_fingerprint`,
`lease_generation`, `lease_token`, `lease_expires_at`, `reserved_bytes`,
`pending_storage_key`, `created_at`, `updated_at` and `completed_at`.

The request table has an account/idempotency unique key and stores its
operation/fingerprint. Add only lookup indexes. Do not alter existing Document
Operation or Image Operation tables.

- [ ] **Step 3: Classify the export request as a narrow private POST**

Mirror the exact image-export predicate in `app.py`, but require:

```python
request.method == "POST"
and request.url.path.startswith("/api/v1/document-operations/")
and request.url.path.endswith("/export-to-asset-vault")
```

Validate the six path segments and canonical UUID before selecting a small
export rate limit. Keep it out of the expensive document parser run gate and
mark response/PWA handling as private like existing Document Operations.

### Task 3: Build the sealed Document Operation source contract

**Files:**

- Modify: `copyfast_document_operations.py`
- Modify: `tests/test_document_operation_asset_export.py`

- [ ] **Step 1: Define the exact export allow-list**

```python
DOCUMENT_OPERATION_EXPORT_KINDS = frozenset({
    PDF_SPLIT_KIND, PDF_MERGE_KIND, PDF_OPTIMIZE_KIND, IMAGE_TO_PDF_KIND,
    PDF_TO_WORD_KIND, PDF_OCR_WORD_KIND, IMAGE_OCR_KIND, PDF_OCR_KIND,
})
DOCUMENT_OPERATION_EXPORT_MEDIA = frozenset({
    (".pdf", "application/pdf"),
    (".docx", DOCX_MEDIA_TYPE),
    (".txt", "text/plain; charset=utf-8"),
})
```

Keep `PDF_TO_IMAGES_KIND` excluded, including its single-page PNG case.

- [ ] **Step 2: Implement `open_document_operation_export_source`**

The helper accepts only account ID and operation ID. It queries one
owner-scoped completed row, derives extension/MIME/filename from
`_output_spec`, requires row metadata to match that canonical contract, and
opens the source through the existing descriptor-pinned verified stream. Its
immutable return object contains only server-derived account/operation/project
IDs, kind, filename, extension, media type, byte size, digest and stream.

```python
if kind not in DOCUMENT_OPERATION_EXPORT_KINDS or state != "completed":
    return None
suffix, media_type, filename = _output_spec(kind, output_page_count=output_pages)
if (suffix, media_type) not in DOCUMENT_OPERATION_EXPORT_MEDIA:
    return None
```

Close the stream on every failed validation path. Never emit its path, digest
or bytes in an envelope.

- [ ] **Step 3: Prove output artifact shape before transfer**

Use exact server parsers after opening the pinned source: strict PDF parse,
bounded DOCX archive with `word/document.xml`, and strict non-empty UTF-8 TXT.
The source's byte size and SHA-256 must still match the operation row.

### Task 4: Add a fenced Asset Vault document exporter

**Files:**

- Modify: `copyfast_assets.py`
- Modify: `tests/test_document_operation_asset_export.py`

- [ ] **Step 1: Add document-specific lease/request dataclasses and reserve API**

Mirror the image-export state machine with new document table names. The
reservation must bind the account, operation UUID, source fingerprint and
expected byte size. A completed relation returns the current receipt; a live
lease returns pending; only an expired current lease can be reclaimed by a
higher generation.

- [ ] **Step 2: Copy and revalidate only the exact artifact contract**

Use an exclusive staging file, rehash the source, hard-link promotion to a new
Vault object, then re-open the final object through Asset Vault's private
reader. Dispatch validation by `(extension, content_type)`:

```python
if extension == ".pdf":
    return _verify_export_pdf(stream, expected_bytes, expected_digest)
if extension == ".docx":
    return _verify_export_docx(stream, expected_bytes, expected_digest)
if extension == ".txt":
    return _verify_export_utf8_text(stream, expected_bytes, expected_digest)
return False
```

The functions must use bounded reads and reject symlinks, archive expansion,
incorrect MIME, empty text, parse errors, hash/size drift and unknown types.

- [ ] **Step 3: Commit metadata only under the live lease fence**

Insert `web_asset_files` with server-derived display/original filename,
extension, content type, byte size and digest. Resolve `project_id` only if it
is still an active project of the same account. Update the export relation
with the same generation/token/expiry predicate, write one
`web.document_operation.export_to_asset_vault` audit event and clear pending
lease fields. If the fence loses, remove the copied file and return no asset.

- [ ] **Step 4: Add current receipt and cleanup helpers**

Replays must reread the Asset Vault lifecycle and return no stale cached
success. Interrupted pending exports may be reclaimed only after lease expiry;
orphan staging/object cleanup must not remove a current asset.

### Task 5: Wire the CSRF route and truthful portal action

**Files:**

- Modify: `copyfast_document_operations.py`
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal.js`
- Modify: `tests/test_document_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Add the route after operation detail and before generic download routes**

```python
@router.post("/{operation_id}/export-to-asset-vault")
async def export_document_operation_to_asset_vault(
    operation_id: str,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    account: dict = Depends(require_csrf),
):
```

It calls `open_document_operation_export_source`, reserves/finalizes only a
live lease and returns standard guarded/pending/completed envelopes. It must
not call `copyfast_bridge`, browser uploads, a provider, wallet or payment.

- [ ] **Step 2: Add the gated client capability and action**

Use one capability key:

```javascript
"document-operation-export-to-asset-vault": Boolean(
  account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && documentOperationExportEnabled
)
```

The action uses `acquireSubmission`, sends an empty POST body plus
`Idempotency-Key`, refreshes current document history and Asset Vault on a
completed receipt, and handles pending/guarded states without claiming an
asset.

- [ ] **Step 3: Render an export control only for eligible completed cards**

The card receives hidden `__documentOperationId`, confirmation copy and no
source bytes/path/URL. Ineligible PNG/ZIP, pending, failed, guarded and
unavailable records show no export action. The portal contract test must
assert CSRF, idempotency, private no-cache behavior and forbidden
Bot/provider/wallet/payment terms.

### Task 6: Document, audit and verify the finished slice

**Files:**

- Create: `docs/migration/DOCUMENT_OPERATION_ASSET_EXPORT_CONTRACT.md`
- Modify: generated `docs/migration/*` and `reports/migration/*` only via the static audit
- Modify: `tests/test_migration_audit.py` only if a new explicit assertion is required

- [ ] **Step 1: Document exact eligible types and non-goals**

State that the export is Web-native, server-side, owner-scoped and not a
`docflow` callback/bridge/provider/payment action. Name excluded ZIP/PNG
output and private fallback behavior.

- [ ] **Step 2: Run focused verification**

```powershell
python -B -m pytest -p no:cacheprovider -q tests/test_copyfast_document_operations.py tests/test_document_operation_asset_export.py tests/test_document_operation_asset_export_portal_contracts.py
python -B -m py_compile copyfast_document_operations.py copyfast_assets.py copyfast_db.py copyfast_api.py app.py
node --check static/portal/integration.js
node --check static/portal/portal.js
git diff --check
```

Expected: the focused suite has zero failures; no Bot/provider/payment/wallet
file is changed; no document export produces a fake or public output.

- [ ] **Step 3: Regenerate and verify migration evidence**

After the source commit, run the existing static-only audit against frozen Bot
SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`, commit only generated
evidence, then run `--verify-web-evidence` with the final HEAD SHA.

- [ ] **Step 4: Review, push and merge one PR**

Inspect the full diff and protected comparators, obtain independent review,
push without force, wait for CI and merge only if green. Do not deploy Railway,
change ENV values, call a paid provider, mutate wallet/payment or claim live
success.
