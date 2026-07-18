# Subtitle Asset Operations contract

`/api/v1/subtitle-asset-operations` is a bounded, private Web-native helper
for a signed account's existing **Asset Vault** SRT/VTT files. It validates a
portable caption subset and can convert `SRT → VTT` or `VTT → SRT` into a new
private attachment.

It complements the manually authored Subtitle Studio; it does not replace it
and does not make ASR, translation, dubbing, media extraction, mux/burn-in or
provider execution available.

## Scope and lifecycle

| Surface | Contract |
| --- | --- |
| `POST /api/v1/subtitle-asset-operations/validate` | Validate one active SRT/VTT source; completes without an output file. |
| `POST /api/v1/subtitle-asset-operations/convert` | Convert one active SRT/VTT source to the other format. |
| `GET /api/v1/subtitle-asset-operations` / `/{id}` | Owner-scoped metadata and lifecycle only. |
| `GET /api/v1/subtitle-asset-operations/{id}/download` | Owner-scoped conversion attachment only after revalidation. |

Lifecycle is `queued → processing → completed`. Input, semantic, storage,
quota or lifecycle failures become `failed`; a missing/corrupt completed
output becomes `unavailable`. A validation record is deliberately
`completed` with `output_available=false`: it never pretends to create a
file.

The browser submits only an Asset Vault UUID, a fixed target format for a
conversion, and an idempotency key. It cannot submit subtitle bytes, text,
filesystem paths, storage keys, URLs, source hashes, output names, MIME types
or provider options.

## Strict portable subtitle subset

- UTF-8 or UTF-8 BOM only; input/output each at most **96 KiB**.
- At most **500** ordered, non-overlapping cues; each cue at most **5,000**
  characters; timestamps are integer milliseconds within **24 hours**.
- SRT uses canonical numeric cue order. VTT uses `WEBVTT` plus a blank header
  line. VTT metadata, cue IDs/settings, `NOTE`, `STYLE`, `REGION` and
  `X-TIMESTAMP-MAP` are rejected rather than silently dropped.
- A missing blank line between cues, malformed timing, unsafe control input or
  dangerous script/data URI caption token is rejected. Conversion only
  normalizes the container/timestamp notation and proves the semantic cue hash
  is unchanged.

## Private storage and delivery

1. Source lookup is active-state and owner-scoped, with exact canonical pairs:
   `.srt` / `application/x-subrip` and `.vtt` / `text/vtt`.
2. The source is read through a descriptor-pinned Asset Vault stream, then
   rechecked against byte size, SHA-256, storage key and lifecycle revision
   before completion.
3. A conversion writes a generated filename to an isolated root under
   `outputs/`, verifies bytes, digest and parsed semantics before and after an
   atomic publication, and only then stores `completed`.
4. Every list/detail rechecks a candidate output before reporting it available.
   Download pins the output descriptor, rehashes/parses it into an anonymous
   sealed stream, and sends a server-owned attachment filename/MIME with
   `no-store, private`, `nosniff`, `no-referrer`, `sandbox` and
   `Cross-Origin-Resource-Policy: same-origin`.
5. Output root is distinct from Asset Vault, Project Packages, Document/Image
   Operations and `/static`. Reconciliation marks interrupted work failed,
   detects tamper/loss, and removes stale unreferenced staging/output files.

## Configuration and protection

The feature is disabled by default. A local executor is intentionally limited
to one attested SQLite replica; an enabled deployment fails closed without all
of these values:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_SUBTITLE_ASSET_OPERATIONS_ENABLED=true
WEBAPP_SUBTITLE_ASSET_OPERATIONS_ROOT=/data/toanaas_webapp_subtitle_asset_operations
WEBAPP_SUBTITLE_ASSET_OPERATIONS_TOPOLOGY=sqlite_single_replica
WEBAPP_REPLICA_COUNT=1
WEBAPP_SUBTITLE_ASSET_OPERATIONS_QUOTA_KB=1024
```

The routes use signed session ownership, CSRF on writes, bounded raw request
bodies, independent rate limits, immutable idempotency fingerprints, account
output quota, audit events and state-transition history. Generic Jobs/Assets
may project a completed conversion only while this feature remains enabled;
the projection performs the same descriptor/hash/semantic availability check
before it exposes a ready download, and never exposes source IDs, paths,
storage keys, hashes, idempotency data or failure internals. Retrying an
existing idempotency receipt replays its immutable result even if its source
has subsequently been archived; a new receipt still requires an active source.

## Explicit non-goals

- No Bot/Core Bridge call, Telegram upload/download, provider call, paid API,
  ASR, translate, dubbing, TTS, FFmpeg, media URL fetch, subtitle extraction,
  video mux/burn-in, background worker, webhook, wallet/Xu/PayOS action.
- No public URL, streaming/preview/player, browser/PWA cache, raw file
  download from a static directory, or fake completed output.
