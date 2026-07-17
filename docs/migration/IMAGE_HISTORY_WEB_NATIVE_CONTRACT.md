# Image History — Web-native contract

## Scope

`/image/history` is a signed, read-only Web Workspace projection over verified
PNG artifacts produced by these two **Web-native** operation kinds only:

- `image_resize` — Resize & Aspect Studio
- `image_enhance` — Image Enhance Studio

The route reads `GET /api/v1/image-operations?limit=<bounded>&offset=<bounded>`
without a `kind` filter. The server remains responsible for the authenticated
account scope, kind allow-list, pagination bounds, metadata redaction and
storage reconciliation. The browser narrows the response again to those two
kind values before rendering it.

## Readiness and pagination

The route is `WEB_NATIVE` only when both of these server flags are true:

- `WEBAPP_ASSET_VAULT_ENABLED`
- `WEBAPP_IMAGE_OPERATIONS_ENABLED`

It intentionally does **not** require `WEBAPP_IMAGE_RESIZE_ENABLED` or
`WEBAPP_IMAGE_ENHANCE_ENABLED`: creation may be paused while a customer still
needs to see or download a previously verified artifact. Until the signed read
completes the page is `processing`; a failed read clears its projection and
returns to `guarded`. It never displays data carried from a prior route.

Pagination is offset-based, bounded by `OPERATION_HISTORY_LIST_LIMIT`, and
uses only the server-projected `previous_offset` / `next_offset`. The page
does not query by filename, raw path, account identifier or provider data.

## Download boundary

The only download action is:

`GET /api/v1/image-operations/{operation_id}/download`

The server re-checks signed session, ownership, operation state, validated PNG
metadata, checksum and file integrity before it streams the file. A row that
is not completed or not download-ready has no download link. There is no
public preview, static output URL, raw filesystem path, browser blob fallback
or PWA/private response cache.

## Explicit non-goals

This history does **not** include or mutate:

- Telegram Bot jobs, Bot delivery history, Core Bridge records or bot assets;
- provider-generated image, upscale, image-to-image or background-removal
  outputs;
- wallet Xu, PayOS, pricing, charge, refund, webhook or ledger state;
- the original Asset Vault source file, which remains unchanged.

**No Bot bridge:** this route does not call or proxy the Telegram Bot/Core
Bridge. **No public preview URL:** a validated private download is the only
file access path.

The page makes no provider/Bot/PayOS request and does not create an output,
job, payment or webhook. Any new image operation must start from its dedicated
Web-native Studio, and an unavailable/guarded record is shown honestly rather
than replaced with simulated output.
