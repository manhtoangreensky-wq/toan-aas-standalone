# Asset Vault — Web-owned private storage contract

Status: **WEB_NATIVE_LOCAL_TESTED**. This slice adds a private customer file
library to the standalone Web App. It does not call the Bot, a media provider,
PayOS, or a wallet service.

## Authority boundary

| Surface | Owner | Explicitly not this feature |
| --- | --- | --- |
| Web Asset Vault files and metadata | Signed Web account | Bot job output/delivery, provider staging, Xu, PayOS, Telegram identity |
| `/assets` and `/api/v1/assets` | Canonical Bot companion | Web Asset Vault blobs |
| `/asset-vault` and `/api/v1/asset-vault` | Standalone Web App | Public/static file hosting |

A Vault file is customer-owned input/reference material. It never becomes a
job input, generated output, delivery, quote, charge or provider request by
itself. A future execution adapter must introduce its own owner/consent,
content-policy, job, idempotency and delivery contract.

## Enablement and persistent storage

The feature defaults off:

```text
WEBAPP_ASSET_VAULT_ENABLED=false
WEBAPP_ASSET_VAULT_MAX_FILE_MB=25
WEBAPP_ASSET_VAULT_QUOTA_MB=250
```

When deliberately enabled in production:

```text
RAILWAY_VOLUME_MOUNT_PATH=/data
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
```

`WEBAPP_ASSET_VAULT_ROOT` must be absolute and a *child* of the real mounted
volume. The application fails startup if it is relative, within `static`, the
volume root itself, or outside the volume. Local/test mode uses an isolated
sibling of `WEBAPP_SESSION_DB_PATH` when a root is not declared. The feature
uses private generated object keys below `objects/`; browser filenames and
paths are never used as filesystem locations.

The first release assumes one persistent-volume replica. Scaling beyond that
requires an object-storage adapter with the same ownership, integrity and
private-download guarantees; do not enable multi-replica storage against a
local Railway volume.

## API and security controls

```text
GET  /api/v1/asset-vault
GET  /api/v1/asset-vault/{id}
POST /api/v1/asset-vault/upload
GET  /api/v1/asset-vault/{id}/download
POST /api/v1/asset-vault/{id}/archive
```

- Every read requires a signed server session and is owner scoped.
- Every write requires signed session, CSRF and an `Idempotency-Key`.
- Upload keys bind to a digest of file + safe metadata. Reusing a key for
  different content is rejected; a matching completed request replays safely.
- Upload streams to a private staging file, enforces account quota and file
  size, verifies extension/MIME, magic/container boundaries, bounded DOCX
  archives and UTF-8 text, then atomically promotes a server-generated key.
- Metadata stores no raw blob or browser filesystem path. API responses omit
  internal storage keys and SHA-256 values. Audit records contain only asset
  ID, byte count and canonical MIME—not filename, path, content or hash.
- Downloads validate active state, owner, size and SHA-256 before a
  `Content-Disposition: attachment` response with `no-store, private`,
  `nosniff`, `no-referrer` and CSP sandbox headers.
- Archive is a reversible-product-state boundary only: it removes the file
  from active listing/download without erasing the private blob, and it does
  **not** free account quota. No browser delete or public share link exists in
  this release.

The PWA caches only named public shell resources and never caches
`/api/v1/asset-vault` requests or downloads.

## Local verification

```powershell
python -m pytest -q tests/test_copyfast_assets.py
python -m pytest -q tests/test_copyfast_projects.py tests/test_portal_safety_contracts.py
```

The tests cover CSRF, idempotency/replay mismatch, MIME/magic/path guards,
quota, owner isolation, archive behavior, download headers/integrity, audit
redaction, storage-volume validation and the no-bridge boundary.
