# Web-native Output Lineage & Handoff Contract

This module joins existing Web-native outputs, the private Workboard and
Content Handoff without changing the Telegram Bot, a provider, PayOS, wallet
or the delivery authority.

## Opaque references

- `wnj:v1:*` identifies a supported Web-native job read model.
- `wna:v1:*` identifies an Asset Vault record.
- Both identifiers remain opaque.  A client never receives the decoded
  database ID, storage key, checksum, provider handle or download URL from a
  Workboard reference or Handoff lineage response.

`wnj:v1:video-operation:*` can identify only a sealed `video_poster` JPEG
output. It is not an alias for the selected Asset Vault source and cannot be
used to create another poster, open a source video, invoke FFmpeg, change a
poster position or reveal runtime/attempt details.

Workboard accepts `native_job` for owner-scoped coordination in any existing
state, and `native_asset` only while the owner-scoped Asset Vault record is
active.  A Workboard card is metadata only: it cannot start a job, claim an
output, charge a wallet, call a provider or publish anything.

## Content Handoff

`references.native_refs` is a revisioned, history-preserved list of:

```json
[
  {"ref_type": "native_output", "ref_id": "wnj:v1:..."},
  {"ref_type": "native_asset", "ref_id": "wna:v1:..."}
]
```

The server checks syntax, owner scope and lifecycle inside the same write
transaction that persists the handoff revision.

- `native_output` is accepted only when its job is exactly `completed` and
  the existing read model has a sealed output.
- `native_asset` is accepted only when its Asset Vault record is `active`.
- References are bounded to 12 and deduplicated by `(ref_type, ref_id)`.

`GET /api/v1/content-handoffs/records/{id}/lineage` is signed-account,
owner-scoped and returns only the opaque reference, lifecycle status,
availability, and (for a currently sealed output) filename, media type and
byte size.  A later missing/archived/invalid source is reported as
`unavailable`; it never recreates a download, output, provider result or
external delivery claim.

## Deliberate boundaries

The module never imports the Telegram Bot, calls Core Bridge or a provider,
starts jobs, mutates wallet/payment state, sends notifications, creates a
social publish action or validates an external delivery.

Video Poster lineage remains subject to its own disabled-by-default runtime,
owner checks and private output verification. A Workboard or Handoff reference
does not bypass those gates and cannot turn the bounded request-time operation
into a durable worker. See
[`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md).
