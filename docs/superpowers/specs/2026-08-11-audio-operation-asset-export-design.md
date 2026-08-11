# Audio Asset Operation → Asset Vault Export Design

## Goal

Let the signed owner deliberately retain one verified, completed MP3 or M4A
Audio Asset Operation output as a new active Asset Vault asset. The resulting
asset can later be selected by existing owner-scoped workflows, including a
manual Content Handoff draft, but this slice never creates a handoff record.

## Selected approach

Add one opt-in `POST /api/v1/audio-asset-operations/{operation_id}/export-to-asset-vault`
endpoint behind a new default-off feature flag. It follows the existing Image
and Document operation export model:

```text
completed + verified Audio transform output
  -> explicit owner request with CSRF + opaque idempotency key
  -> fenced reservation / short lease
  -> server re-verifies private output and copies it to Vault staging
  -> hashes the staged Vault object, atomically publishes it, and creates one active asset row
  -> completed receipt with an opaque Asset Vault UUID
```

The Portal adds a distinct **Lưu vào Asset Vault** control next to a download
action only for completed `audio_convert` or `audio_normalize` operations with
`output_available === true`. It sends only the Audio Operation UUID and a
generated idempotency key; it never sends bytes, a path, filename, format,
hash, provider handle, or an Asset Vault ID.

The Portal bootstrap must preserve the bounded Audio Operations projection,
its read states, and this export capability after hydration. Without that
projection, an otherwise valid server receipt can be silently dropped before
the completed-operation control is rendered.

## Server boundary

- A new `WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED` code flag defaults to
  false. This change does not add or change a deployed environment value.
- Only `audio_convert` and `audio_normalize` outputs with a canonical completed
  MP3/M4A descriptor are exportable. `audio_inspect`, pending, failed,
  guarded, unavailable, stale, foreign, malformed, or mismatched output is
  rejected truthfully and cannot create an asset.
- Export persistence is separate from Document and Image export tables. Its
  relation is one Audio Operation to at most one Asset Vault asset, with a
  per-account idempotency map, lease generation/token/expiry, reserved byte
  accounting, and an immutable request fingerprint.
- The finalizer copies from a server-opened Audio Operations stream to a Vault
  staging object, recomputes size/SHA-256, validates the closed MP3/M4A
  descriptor, publishes atomically, and creates the Asset Vault record only
  while holding the current lease. A stale writer cannot finalize or delete a
  newer attempt.
- Both source and destination remain owner-scoped. The response exposes only
  the existing public Asset Vault projection and a Vietnamese status envelope.

## Explicit non-goals

- No Bot/Core Bridge change, Telegram callback, provider call, AI music/TTS,
  job, wallet/Xu change, PayOS action, webhook, payment, public URL, browser
  FFmpeg, or direct filesystem path.
- No auto-export after audio conversion and no automatic Content Handoff,
  external delivery, publishing, notification, player, or PWA cache behavior.
- No replacement, deletion, or mutation of the original Audio Operations
  output or source Asset Vault asset.

## Rejected alternatives

1. **Direct Content Handoff from Audio Operations:** rejected because a
   private output must first become an independently verified, lifecycle-aware
   Asset Vault asset; creating a coordination record is a separate explicit
   owner action.
2. **Auto-copy every completed transform:** rejected because storage retention
   is a material user decision and must not happen just because a transform
   succeeded.
3. **Reuse Document/Image export tables:** rejected because Audio output has a
   different source root, descriptor and retention boundary; sharing relations
   would weaken auditability and foreign-key meaning.

## Acceptance evidence

1. Feature flag, CSRF, owner scope, idempotency collision/replay, lease race,
   stale output, corrupted output, output unavailability, and path traversal
   cases cannot create a second or unsafe Vault asset.
2. A verified completed MP3/M4A output becomes exactly one active private Vault
   asset with a server-owned filename/content type, matching bytes and digest.
3. The Portal renders export only for eligible transform receipts; it reuses a
   single submission fence, refreshes signed state, and never calls a provider,
   Bot, wallet/payment, PayOS, Content Handoff write, or browser byte API.
   Its normalized bootstrap preserves only the bounded Audio Operations
   projection needed to render this owner-scoped action.
4. Existing Audio Operation download behavior, Document/Image exports, Asset
   Vault ownership checks, service-worker privacy policy, and Content Handoff
   active-asset selection remain unchanged.
