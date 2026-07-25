# Audio Change Request — Web-native confirmation contract

## Purpose

`/api/v1/audio-change-requests` adds a narrow, durable confirmation flow to
an **active Audio Hub collection item** that already references an owned Audio
Asset Vault file. It is not a Bot callback replay and it does not replace the
existing direct `/api/v1/audio-asset-operations/*` utility surface.

The flow is enabled only when all relevant local Web switches are enabled:

```text
WEBAPP_AUDIO_CHANGE_REQUESTS_ENABLED=true
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_AUDIO_ASSET_OPERATIONS_ENABLED=true   # required for estimate/confirm runtime checks
```

`WEBAPP_AUDIO_CHANGE_REQUESTS_ENABLED` is false by default. Enabling it never
enables a Bot/Core Bridge path, provider, catalog, AI music/voice request,
canonical Bot job, wallet/Xu, PayOS, price quote, payment, refund, public URL
or browser-side audio process.

## Route ownership

| Surface | Scope | Authority |
| --- | --- | --- |
| `/audio-hub/{collection_id}` | Customer UI only | Existing signed Media Workspace collection detail plus this request read model |
| `POST /api/v1/audio-change-requests/drafts` | Create a durable request snapshot | Web-native owner-scoped request store |
| `POST /api/v1/audio-change-requests/drafts/{id}/estimate` | Validate snapshot and create a non-monetary plan | Web-native preflight only |
| `POST /api/v1/audio-change-requests/drafts/{id}/confirm` | Explicitly link one existing local Audio Asset Operation | Existing verified local executor |
| `GET /api/v1/audio-change-requests/drafts[/{id}]` | Read owner-scoped status | Web-native request + verified operation projection |

The board is deliberately absent from `/media-workspace/{collection_id}`. The
existing Audio Hub remains a visual route alias over `/api/v1/media-workspace`;
this module adds a separate request authority rather than changing that alias
or introducing an `/api/v1/audio-hub` namespace.

## Lifecycle

```text
draft -> awaiting_confirm -> queued|processing|completed|failed|guarded|unavailable
```

1. **Draft** accepts only a collection UUID, attached media-item UUID, closed
   operation (`inspect`, `convert_mp3`, `convert_m4a`, `normalize`) and an
   idempotency key. The server rechecks signed ownership, active collection,
   attachment, active Asset Vault source and captures collection/source
   revisions. It does not start FFmpeg or create output.
2. **Estimate** requires CSRF, request revision and a new idempotency key. It
   rechecks the captured attachment/source and validates the server runtime
   configuration only. Its deterministic plan contains fixed output profile
   information and `requires_confirmation=true`; it contains no amount, price,
   quote, credit, ETA, payment or provider fields and never probes/renders
   audio.
3. **Confirm** requires CSRF, current request revision, `confirm: true` and
   idempotency. It rechecks the same snapshot once before the call and again
   atomically inside the Audio Asset Operation reservation transaction. Only
   then can it create or replay the one stable local operation.
4. **Status** reflects the linked operation after fresh private-output
   verification. A transform is never presented as completed if its output
   cannot still pass the existing integrity check; it becomes `unavailable`.
   An inspect may complete with `output_available=false` because it produces no
   file by design.

Any collection revision change, detach, archive, source lifecycle change,
digest/size mismatch or missing active source guards the request before an
operation is reserved. The user must create a fresh draft after such a change.
Detaching an item itself remains a normal Media Workspace operation: the
request keeps only an immutable historical item ID/snapshot and is shown as
guarded rather than blocking the detach or silently disappearing from history.

## Security and data boundaries

- Signed session and server-side account ownership guard every endpoint.
- All writes require CSRF, bounded request body, route-family rate limit and
  idempotency with payload fingerprints.
- The request table stores only UUIDs, fixed operation/profile values and
  immutable source revision/digest evidence. It stores no source bytes, local
  path, storage key, free-text brief, license note, provider response or
  payment data.
- Browser state receives only bounded request/operation metadata. It does not
  receive source digest, Asset Vault ID, storage key, raw URL or local path.
- The existing Audio Asset Operations executor remains the only component that
  can invoke its server-owned FFmpeg/ffprobe command and publish a private
  output. Existing rehash/reprobe/atomic publication and sealed attachment
  download rules remain unchanged.
- A stable operation idempotency key is derived server-side from the request
  UUID. Concurrent confirmations may observe the same operation but cannot
  reserve or charge a second one.
- No request creates a generic Job, asset fallback, PWA private cache, public
  player, waveform, preview, media stream or automatic handoff.

## Explicit exclusions

- Bot `music_quick|*`, `sfx_quick|*`, `media_quick|*` and `suggest_music|*`
  callbacks remain source-review boundaries and are never accepted here.
- No Suno, Key4U, music/SFX catalog, external model/provider, clone, TTS,
  ASR, dubbing, translation, music generation, payment or Telegram delivery.
- The request plan is not a commercial quote, license clearance, rights
  verification, approval or release decision.
