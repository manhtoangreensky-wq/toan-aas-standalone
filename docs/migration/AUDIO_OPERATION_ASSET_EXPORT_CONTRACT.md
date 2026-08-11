# Audio Asset Operation to Asset Vault export contract

## Purpose and scope

This contract lets the signed owner explicitly retain one verified, completed
Web-native Audio Asset Operation output as a separate private Asset Vault
asset. It is a copy boundary, never a new audio generator or a replacement for
the original operation.

The route is disabled unless all of these flags are enabled on the Web service:

- `WEBAPP_ASSET_VAULT_ENABLED`;
- `WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED`;
- `WEBAPP_AUDIO_ASSET_OPERATION_EXPORT_ENABLED`.

The public bootstrap exposes only the effective boolean capability. The
browser additionally needs its current signed account and CSRF token.

## Closed artifact boundary

Only a completed owner-scoped `audio_convert` or `audio_normalize` output may
be exported. The server derives every descriptor from its sealed operation
record and accepts only:

| Output | Retained Asset Vault artifact |
| --- | --- |
| MP3 transform | `.mp3`, `audio/mpeg`, MP3 probe/byte/hash contract |
| M4A transform or `speech_safe_v1` normalization | `.m4a`, `audio/mp4`, AAC/MP4 probe/byte/hash contract |

Inspect-only, queued, processing, failed, guarded, unavailable, stale,
foreign, malformed or tampered outputs are not exportable. The browser cannot
supply bytes, paths, filenames, MIME types, hashes, source asset IDs, a target
format, a provider handle or a Vault destination.

## Request and response boundary

The single write endpoint is:

```text
POST /api/v1/audio-asset-operations/{operation_id}/export-to-asset-vault
```

It requires a signed owner, CSRF token and opaque `Idempotency-Key`. The route
accepts an empty body; the operation UUID is the only browser-selected value.

- `completed` returns one current, redacted active Asset Vault receipt.
- `processing` means a current fenced copy lease owns the operation; no asset
  is claimed yet.
- `guarded` or `unavailable` means ownership, eligibility, integrity or output
  availability could not be verified; no substitute asset is fabricated.

The Portal offers **Lưu vào Asset Vault** only beside an eligible completed
transform's private download. It uses a submission fence, sends the opaque
operation UUID in the URL with the idempotency header, and refreshes Audio
Operations plus Asset Vault from the server before showing success.

## Private copy lifecycle

1. The audio route checks the effective flags, signed owner, CSRF and rate
   limit, then derives the completed output descriptor only from the
   owner-scoped database row.
2. The Asset Vault reserve helper writes an account-scoped idempotency mapping
   and a short, fenced copy lease before any private output bytes are opened,
   hashed or probed.
3. A bounded worker opens and verifies the private stream under the existing
   single-media probe gate, then copies it to a new Vault staging object with
   bounded byte counting and SHA-256 verification.
4. The destination is re-opened, pinned and checked for its closed MP3/M4A
   magic/probe contract before publication.
5. Only the current lease may atomically publish one active `web_asset_files`
   row. Stale attempts cannot overwrite, delete or finalize a newer lease.

Audio export reservations count against the existing per-account Asset Vault
quota. The persistence tables are separate from Image and Document export
relations, so their source type and lifecycle remain auditable.

## Non-goals and privacy boundary

- No Bot/Core Bridge, Telegram callback, provider, TTS/ASR, FFmpeg browser
  execution, wallet/Xu, PayOS, webhook, public URL or production ENV change.
- No automatic export after conversion, no Content Handoff write, no publish,
  notification, player, PWA cache or external delivery.
- The original Audio Operation output and its source Asset Vault asset are not
  replaced, removed or mutated.
- Downloaded retained assets remain signed-session, owner-scoped Vault files;
  raw storage keys, hashes and private paths never enter the browser response.

## Focused verification

`tests/test_audio_operation_asset_export.py` covers capability gates, CSRF,
owner scope, idempotency replay/collision, MP3/M4A output, stale lease,
tampered/unavailable source, descriptor mismatch, server-stream provenance and
private response redaction. `tests/test_audio_asset_operations_portal_contracts.py`
covers the capability-gated Portal control and same-origin action boundary.
