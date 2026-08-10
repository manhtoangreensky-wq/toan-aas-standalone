# Superseded — Image Operation → Asset Vault Export Design

> Do not implement this initial draft. The reviewed implementation authority is
> [the fenced design](2026-08-10-image-operation-asset-export-fenced-design.md),
> which adds lease fencing, quota reservation, lifecycle-truthful replay and
> descriptor-safe copying.

## Decision

The next Web/App vertical slice is an explicit, server-side handoff from a
verified local Image Operation PNG into the signed account's Asset Vault.
It makes existing real local work reusable in later Web-owned workflows
without treating it as a Bot result, provider output, job, payment, or public
delivery.

The user-facing flow is intentionally narrow:

```text
Asset Vault input
  → Resize / Enhance / Plain-background cleanup / Brand Overlay
  → verified private PNG output
  → explicit customer confirmation
  → new independent Asset Vault file
```

The browser sends only an opaque Image Operation UUID in the path and an
idempotency key in the request header. It never sends image bytes, an output
path, filename, MIME type, checksum, project ID, Bot identifier, provider
value, URL, or a storage key.

## Why this is the correct next slice

The existing Web App already performs bounded, local PNG transforms with
owner-scoped inputs, authenticated writes, output re-validation and private
downloads. At present those outputs are terminal: customers can download
them, but cannot intentionally retain them in the Web-owned library for a
subsequent Studio/Project workflow. That forces needless manual download and
re-upload and weakens the product flow even though the platform has already
validated the file.

This change closes that product gap without expanding into the blocked areas:

- `imgtool|*` remains Telegram source evidence only; it is not decoded or
  mapped to this endpoint.
- AI remove-background, image generation, upscale, provider selection and
  image-to-image remain guarded.
- Storyboard Grid is excluded because its ZIP/scene-cell retention model needs
  its own contract.
- Bot assets, canonical jobs, Core Bridge, wallet/Xu, PayOS, webhooks,
  refunds, provider calls and public URLs remain untouched.

## Exact scope

Only these completed Image Operation kinds are exportable:

- `image_resize`
- `image_enhance`
- `image_background_cleanup`
- `image_brand_overlay`

The endpoint is:

```text
POST /api/v1/image-operations/{operation_id}/export-to-asset-vault
Headers:
  Idempotency-Key: validated opaque key
  X-CSRF-Token: existing same-origin token
```

The endpoint requires all of the following at request time:

1. A valid signed Web session and CSRF token.
2. `WEBAPP_ASSET_VAULT_ENABLED=true`.
3. `WEBAPP_IMAGE_OPERATIONS_ENABLED=true`.
4. `WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED=true`.
5. A UUID owned by the current signed account.
6. An allowed kind, `state='completed'`, canonical `image/png`, positive
   byte size and recorded digest.
7. A descriptor-pinned image-operation output that still passes its strict
   PNG dimensions/mode/transparency validation and digest check.
8. Available Asset Vault quota at commit time.

The operation output is copied—not moved, hard-linked or re-used by path—into
a freshly generated Asset Vault object key. The output and saved asset keep
independent retention/lifecycle. Archiving or later invalidating either one
does not rewrite the other.

## Persistence and idempotency

Add an additive `web_image_operation_asset_exports` relation keyed by
`operation_id`, with `account_id`, `asset_id`, server-derived request
fingerprint, state and timestamps. The relation gives one completed Asset
Vault export per Image Operation and prevents a double click, retry or
different idempotency key from creating duplicate stored copies.

The export has two durable phases:

1. Reserve a small pending relation inside SQLite before copying bytes.
2. Stream the already-pinned output to Asset Vault staging; rehash and
   validate its PNG signature; atomically promote a new private object; then
   insert the Asset Vault metadata, finish the export relation and store the
   idempotent receipt in one database transaction.

A bounded stale pending reservation may be reclaimed safely. If an
interruption leaves a promoted file without metadata, the existing Asset Vault
orphan reconciler removes it after its normal retention window. If an existing
completed relation references an archived/unavailable asset, the endpoint
returns the existing relation truthfully rather than creating a second copy.

## Data, privacy and delivery boundary

The exported Asset Vault row uses server-derived metadata:

- deterministic display label based only on the local operation kind;
- deterministic PNG filename based only on the local operation kind;
- `image/png`, `.png`, byte size and digest derived from verified bytes;
- the server-stored Image Operation project only if it is still active and
  owned; otherwise no Project link is invented.

Public responses contain only existing safe Asset Vault metadata plus opaque
operation/asset IDs and an export state. They never expose a filesystem path,
object key, hash, raw source, content, provider/Bot identifier, job, price,
wallet, payment or delivery URL. The audit event contains only opaque IDs,
operation kind and byte size.

The new API response is `Cache-Control: no-store, private`; the service worker
does not cache this private route, its response, or the Asset Vault output.

## Portal behavior

Each eligible, completed PNG card has one secondary action:

```text
Lưu vào Asset Vault
```

It appears only when the server has exposed the export capability and the
operation is completed with `download_ready=true`. The action uses the portal's
existing confirmation lifecycle, then performs one same-origin CSRF request
with an in-memory idempotency key. It does not auto-save, attach a raw asset
to a URL, fabricate a preview or show a completion state before the server
returns a valid saved-asset receipt.

On success the Portal refreshes owner-scoped operation/Vault data, announces a
sanitized message and offers normal navigation to `/asset-vault`. A disabled,
pending, failed, tampered or non-exportable operation has no action that could
produce a fake Asset Vault entry.

## Security and performance guarantees

- No browser upload/download round-trip; bytes stay server-side and are copied
  in bounded chunks between two private storage roots.
- The source output is opened once through its existing pinned descriptor and
  revalidated before copying. The destination is rehashed and format-checked
  before it gets a metadata row.
- The endpoint receives a narrow early rate-limit bucket before session,
  CSRF, SQLite and storage work.
- A single allowed local output kind list is enforced server-side. Unknown,
  future, provider or Storyboard values fail closed.
- Signed session, CSRF, account ownership, database uniqueness, quota,
  idempotency and audit checks occur server-side. Browser state is only a
  presentation convenience.
- The change does not reduce CSP, cookie, PWA, storage root, symlink, MIME,
  digest, content-disposition or private-download protections.

## Acceptance criteria

1. A signed owner can explicitly save each allowed completed PNG once and
   receive a new active, private Asset Vault row with byte-for-byte validated
   content.
2. Anonymous, missing-CSRF, disabled, foreign, non-completed, unknown-kind,
   stale/tampered or quota-exceeded requests cannot create an asset or leak
   output metadata.
3. Idempotent replays return the same asset; a changed key cannot create a
   second asset for the same operation.
4. The original operation and exported asset lifecycle are independent.
5. The Portal contains no provider/bridge/payment/wallet/Bot call or browser
   byte/path/URL handling in this flow.
6. The final diff is limited to the declared Web App contract, tests,
   migration evidence and documentation. No Bot, Railway, ENV or production
   data changes.
