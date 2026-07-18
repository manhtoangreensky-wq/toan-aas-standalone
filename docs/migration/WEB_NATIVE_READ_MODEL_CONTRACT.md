# Web-native Jobs / Assets read-model contract

## Scope

`copyfast_native_read_models.py` is a query-only projection boundary for the
already-persisted, Web-owned records below:

| Projection | Read source |
| --- | --- |
| Job-like Project Package output | `web_project_packages` |
| Job-like Document Operation output | `web_document_operations` |
| Job-like Image Operation output | `web_image_operations` |
| Job-like Subtitle Asset conversion | `web_subtitle_asset_operations` while `WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED=true` |
| Job-like Video Poster output | `web_video_operations` (`kind=video_poster`) |
| Asset Vault metadata | `web_asset_files` |

The module does not create schema, start a transaction capable of writing,
read a private blob, generate a download URL, call a Bot/Core Bridge/provider,
or read wallet, Xu, payment, PayOS, delivery, publication or worker tables.
It uses `copyfast_db.read_transaction()` only.  Application startup remains
responsible for `ensure_copyfast_schema()` before any read route is enabled.

## Integration surface

The router/adaptor receives the signed account ID from its existing session
dependency and calls only these functions:

```python
from copyfast_native_read_models import (
    get_native_job,
    list_native_assets,
    list_native_completed_outputs,
    list_native_jobs,
)

jobs = list_native_jobs(account_id, limit=100)
job = get_native_job(account_id, public_id)  # dict or None
assets = list_native_assets(account_id, limit=100)
completed_outputs = list_native_completed_outputs(account_id, limit=100)
```

All methods are owner-scoped in the SQL predicate.  A foreign record and an
unknown/malformed job ID both return `None` from `get_native_job`; an adapter
should use the same guarded response for both.  `limit` is clamped to `1..100`.
`list_native_completed_outputs` is a separate bounded query of sealed
completed outputs, not a filter over the newest generic jobs page; use it for
Assets so 100 newer queued rows cannot hide an older completed artifact.

The optional helpers `encode_native_job_id`, `parse_native_job_id` (also
available as `parse_public_job_id`), `encode_native_asset_id`, and
`parse_native_asset_id` are for a route/adaptor that needs to validate an ID
before calling the projection.  They use only the current route-safe grammar:

```text
wnj:v1:project-package:<opaque-token>
wnj:v1:document-operation:<opaque-token>
wnj:v1:image-operation:<opaque-token>
wnj:v1:subtitle-asset-operation:<opaque-token>
wnj:v1:video-operation:<opaque-token>
wna:v1:<opaque-token>
```

Every emitted ID matches `[A-Za-z0-9._:-]` and is at most 160 characters (the
existing API/portal route maximum); raw database IDs are never sent as the
public `id` field.

## Public job shape

Each job list/detail item has this common shape:

```json
{
  "id": "wnj:v1:document-operation:...",
  "kind": "document-operation",
  "operation_kind": "pdf_split",
  "state": "completed",
  "status": "completed",
  "created_at": "...",
  "queued_at": "...",
  "started_at": "...",
  "completed_at": "...",
  "updated_at": "...",
  "summary": {},
  "output": {
    "filename": "toan-aas-pdf-split.pdf",
    "content_type": "application/pdf",
    "byte_size": 1234
  }
}
```

`state` and the compatibility `status` are both the exact stored lifecycle
value.  The read model does not normalize, repair, infer, or relabel a state
as successful.  In particular, a row stored as `completed` remains
`completed`, but its `output` is `null` unless all sealed-output metadata is
present and valid for that row type:

- state is exactly `completed`;
- a type-specific generated storage-key shape exists (the key itself is never
  returned);
- the direct handler's required positive byte count, valid SHA-256, and
  type-specific generated storage-key suffix exist; and
- the stored MIME equals the direct handler's exact MIME contract, including
  `text/plain; charset=utf-8` for Image OCR.  PDF-to-images uses PNG only when
  its stored output-page count is exactly one; otherwise it must be ZIP.

This is metadata eligibility only.  It does not claim the blob is physically
downloadable; the existing owner-scoped download handler still verifies the
private file when a user requests it.

Subtitle Asset validation is outputless by design. A completed
`subtitle_validate` projection therefore has `output: null`; only a completed
`subtitle_convert` with an exact `.srt`/`.vtt` private-output contract may
project an attachment. When the optional executor is disabled, its table is
not queried or advertised by this generic read model.

`summary` contains only safe type-specific measurements (for example document
counts or image dimensions).  It never contains source asset IDs, Project IDs,
request/idempotency metadata, event data, filesystem information or failure
implementation details.

For a Video Poster item, `summary` is limited to the requested poster position,
verified source duration/dimensions, selected frame timestamp and verified JPEG
dimensions. Its `output` is eligible only for an exact `video_poster`
`completed` row with an `outputs/<opaque>.jpg` storage-key shape, canonical
`image/jpeg` metadata, a positive byte count, valid hash and positive output
dimensions. The generic projection still does not expose the selected Asset
Vault source ID, output key/path, process details or an executable URL; the
owner-scoped delivery handler re-verifies the private JPEG when downloaded.

## Public asset shape

```json
{
  "id": "wna:v1:...",
  "kind": "asset",
  "name": "brief.pdf",
  "filename": "brief.pdf",
  "extension": ".pdf",
  "content_type": "application/pdf",
  "byte_size": 1234,
  "state": "active",
  "status": "active",
  "created_at": "...",
  "updated_at": "...",
  "archived_at": null
}
```

Asset lifecycle values are likewise exact stored values.  Display/original
filenames are reduced to a basename so an old or manually malformed row cannot
project a local path.

## Redaction and non-goals

No public object includes an account ID, raw row ID, Project ID, source asset
ID, storage key/path, SHA/hash, source snapshot, request fingerprint,
idempotency key, failure code, settings JSON, event history, provider handle,
Bot/Telegram field, worker field, wallet/Xu, payment, PayOS, quote, price, or
delivery URL.  The model is read-only metadata, not a generic job executor or
an alternative download endpoint.
