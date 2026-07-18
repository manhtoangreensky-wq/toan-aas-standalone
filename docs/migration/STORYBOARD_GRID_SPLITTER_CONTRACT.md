# Storyboard Grid Splitter — Web-native contract

`/image/storyboard-grid` turns one verified private image from the signed
account's Asset Vault into a deterministic set of JPEG scene crops, packaged
as a private ZIP with a manifest. It ports the useful grid-cutting semantics
from the local `bot.py` helper without importing Telegram conversation state,
Bot delivery, provider execution, wallet/Xu, PayOS or job records.

It does not read, create or change Telegram identity, Bot assets, Bot jobs,
provider state, Xu, PayOS orders/webhooks or canonical ledger data.

## Input, geometry and output

- API family: `/api/v1/storyboard-grid`.
- Input: one active owner-scoped JPEG, PNG or WebP Asset Vault image; the
  browser sends only its opaque Asset ID and bounded storyboard settings.
- Default grid: **2 rows × 5 columns**. The server derives every crop from
  the canonical source bytes; it never accepts image bytes, a URL, raw path,
  browser canvas output, provider setting or client supplied scene file.
- Compatibility: scene numbering is **row-major** and uses the Bot's
  deterministic `round` partition behavior. `trim_percent` is limited to
  **0–18%** (canonical decimal `0.00–0.18`) and is applied server-side only.
  Episode and start-scene labels are manifest metadata, not Bot conversation
  state.
- Output: one verified, private JPEG-scene ZIP plus a manifest. Scene cells
  retain their grid index, source crop geometry, filename, byte size and hash
  as operation evidence. A result is `completed` only after the ZIP, manifest
  and every referenced JPEG scene satisfy the service's validation contract.

## Lifecycle and security boundary

The normal state progression is `queued → processing → completed` or
`failed`. The service requires a signed Web session, CSRF protection,
owner-scoped Asset Vault lookup, allowed MIME/decoder validation, bounded
pixel/scene/ZIP limits, server-side staging and private persistence. It
rechecks source state and immutable digest after staging, uses idempotency
fingerprints, and keeps request, operation, cell and event data in the
Web-owned additive tables.

Downloads are account-owned verified descriptors only. They are private,
`no-store` responses; there is no static/public output URL, PWA private-file
cache, browser-side ZIP fallback or path disclosure. Reconciliation is a
best-effort private-storage integrity scan after application readiness and
never turns a missing artifact into a fake successful scene pack.

## Configuration

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_IMAGE_OPERATIONS_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_ROOT=/data/toanaas_webapp_image_operations
WEBAPP_STORYBOARD_GRID_ENABLED=true
```

`WEBAPP_STORYBOARD_GRID_ENABLED` defaults to `false`. The feature uses the
existing isolated Image Operations persistence boundary and stays unavailable
unless its own runtime validation succeeds. Disabling it blocks new requests;
the service must not replace a guarded operation with fabricated ZIP or scene
output.

## Explicit non-goals

No AI image generation/edit/upscale, OCR, provider request, Bot bridge call,
Telegram upload/delivery, job creation, Xu change, PayOS/payment/webhook,
public asset, browser image import, source overwrite or fake output.
