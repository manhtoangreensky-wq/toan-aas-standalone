# Private asset delivery contract

This is a Web-only compatibility contract. It does not move assets, change
provider storage, modify `bot.py`, create a second webhook, or let the browser
choose a file owner.

## Customer flow

1. The asset list from the private core exposes only redacted metadata.
2. `download_ready=true` means the Bot validated output metadata; by itself it
   never creates a Web download link.
3. The Bot may additionally expose `delivery_ready=true` for a specific asset.
   Only then does the portal render a same-origin link to
   `GET /api/v1/assets/{asset_id}/download`.
4. The Web server verifies its signed session, derives the canonical Telegram
   identity server-side, requests the private Bot route, and checks the exact
   delivery contract below.
5. The Web server sends one `307` redirect to the signed temporary URL. It
   does not return that URL in JSON, store it, cache it, or derive it from a
   provider path. Each decision is recorded in the Web audit table without the
   URL.

## Job Detail association

The frozen private bridge currently emits an owned asset with the same opaque
identifier as its canonical job. On `/jobs/{id}`, the Portal reads the normal
owner-scoped `/assets` collection and displays an output row **only when** its
asset ID exactly equals the job ID returned by the owner-checked job endpoint.
It does not infer a relationship from feature name, timestamps, provider data,
output metadata or an URL. If a future Bot uses different IDs, it must add a
separate owner-scoped relation contract; the Portal will otherwise show no
asset rather than guessing.

An asset row may link to `/jobs/{id}` using that same already-redacted opaque
identifier. This is a navigation aid only: the Job Detail route repeats its
signed-session ownership check and the link never creates a file URL.

## Required Bot response

The private bridge for `GET /internal/v1/assets/{asset_id}/download` must
return this shape after its own ownership and artifact validation:

```json
{
  "ok": true,
  "status": "completed",
  "message": "internal only",
  "data": {
    "asset_id": "the-requested-asset-id",
    "download_ready": true,
    "delivery_ready": true,
    "delivery": {
      "url": "https://configured-delivery-host/path?opaque-signature",
      "expires_at": "2026-07-11T12:00:00+00:00"
    }
  },
  "error_code": null
}
```

The Web App fails closed unless all of these are true:

- `asset_id` exactly matches the requested validated route ID;
- status is `completed` and both readiness flags are literal `true`;
- URL is HTTPS, has no credentials/fragment/non-standard port, and is at most
  2048 characters;
- `expires_at` is timezone-aware, in the future, and at most one hour away;
- hostname exactly matches an explicit Railway allowlist.

The Web bridge client does not automatically retry this download route. Even
though it is a `GET`, a Bot adapter may mint a new short-lived URL and audit a
delivery decision; it is treated as a credential-issuance boundary rather
than a generic idempotent read.

## Railway configuration

Do not add a provider key or raw signed URL to the Web App. After the Bot
adapter exists, set only hostnames:

```text
WEBAPP_ASSET_DELIVERY_ALLOWED_HOSTS=downloads.toanaas.vn,cdn.example.net
```

There are no wildcards. Leaving it empty keeps every delivery guarded. The
current task does not set this variable or test a live URL.

## Test boundary

Tests mock the private bridge. They verify the canonical identity sent to the
bridge, exact asset ID matching, allowlisted HTTPS redirect, short expiry,
`Cache-Control: no-store`, no-referrer behavior, audit-safe handling, and
rejection without leaking an unapproved URL/token to browser JSON.
