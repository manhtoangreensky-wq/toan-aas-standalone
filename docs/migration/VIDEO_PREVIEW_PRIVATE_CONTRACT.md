# Video Preview & Inspector — private Web contract

Status: **WEB_NATIVE_LOCAL_TESTED** when the explicit feature flag is enabled.
This is an owner-scoped Asset Vault inspection surface, not a Bot playback or
delivery adapter.

## Enablement

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_VIDEO_PREVIEW_ENABLED=true
```

`WEBAPP_VIDEO_PREVIEW_ENABLED` defaults to `false` and is effective only when
the private Asset Vault is already enabled. It does not enable Video Studio,
Bot/Core Bridge, providers, FFmpeg, jobs, wallet/Xu, PayOS, publishing or a
general media service.

## Source and delivery boundary

- The Portal lists only active Asset Vault records owned by the signed Web
  account with an exact `.mp4`/`video/mp4` or `.webm`/`video/webm` pair at or
  below 20 MiB. MOV and loose `video/*` matching are intentionally excluded.
- `GET /api/v1/asset-vault/{id}/preview` repeats owner, state, type, byte-size
  and descriptor-pinned SHA-256 verification. It seals the verified bytes into
  an anonymous temporary stream before delivery.
- The route returns same-origin inline media with `no-store, private`,
  `nosniff`, `no-referrer`, CSP `sandbox`, CORP `same-origin` and an exact
  content length. `Range` is explicitly rejected with `416`; there is no
  server streaming/seek contract.
- Missing, foreign, archived, non-previewable or malformed sources have the
  same generic guarded projection. An integrity failure marks the owner row
  unavailable and emits only a bounded audit event with opaque asset ID,
  format and byte count—never a filename, storage key, path, URL or hash.

## Browser boundary

The browser requests the private endpoint once, validates response status,
MIME, length and security headers, then creates `URL.createObjectURL(blob)`
only in the current tab. It never assigns the API endpoint, a signed URL, a
provider URL or a raw path to the `<video>` element.

The object URL is revoked on replacement, refresh, clear, route/session change
and guarded hydration. Duration and resolution are displayed only after the
browser emits `loadedmetadata`; an unsupported decoder becomes a guarded state,
never a fabricated preview/success. There is no autoplay, local/session
storage, PWA cache, public share, download proxy or output/job record.

## Explicit exclusions

This contract does **not** map Telegram dynamic media-preview callbacks. It
does not access Bot media cache, Telegram file IDs, Core Bridge, provider API,
PayOS, Xu ledger, wallet, jobs, finalization, FFmpeg, asset creation or payment
webhooks. `/video/preview` is a small Web-native extension beside the parity
matrix, not proof of Bot workflow equivalence or production media readiness.
