# Web-native Video Poster Lab contract

Status: **Web-native bounded execution slice; disabled by default.** This is
not a Railway deployment, provider-readiness, Bot-parity, or long-running
video-rendering claim.

Video Poster Lab takes one private video already owned by the signed Web
account in Asset Vault and produces one new private JPEG poster. It is
deliberately separate from Video Studio planning and from the Telegram Bot's
video jobs. It does not read or write Telegram identity, Bot jobs, Xu/wallet,
PayOS orders/webhooks, provider state, or a provider-delivery record.

## API, lifecycle and truthfulness

```text
POST /api/v1/video-operations/poster
GET  /api/v1/video-operations
GET  /api/v1/video-operations/{operation_id}
GET  /api/v1/video-operations/{operation_id}/download
```

The only currently supported `kind` is `video_poster`. A normal bounded
attempt transitions `queued → processing → completed`. Unsafe input or runtime
failure ends as `failed` or `guarded`; an interrupted request is reconciled to
`failed`; a missing or tampered retained output becomes `unavailable`. A
browser must never show a result/download for any state other than a sealed
`completed` artifact.

The direct operation response is owner-scoped and may identify the selected
source Asset Vault item so that the same customer can understand the request.
The generic `/jobs` and `/assets` read models expose only opaque
`wnj:v1:video-operation:*` identifiers and safe dimensions; they redact source
asset IDs, storage keys, hashes, idempotency/failure data, paths and runtime
details.

## Private input, execution and output boundary

1. The browser submits only an active, owner-scoped Asset Vault video ID,
   `poster_position` (`start`, `middle`, or `end`) and an idempotency key. It
   cannot submit bytes, a path, a URL, a binary name, a filter graph, a
   Telegram file ID or a provider handle.
2. Input is restricted to canonical `.mp4`, `.mov`, or `.webm` MIME/extension
   pairs, at most **25 MiB**. The server creates and hashes an isolated copy
   before inspecting it.
3. `ffprobe` is invoked with fixed non-shell argv to verify one primary video
   stream, duration **0.2–120 seconds**, maximum side **4,096 px**, maximum
   **16 MP**, and aspect ratio at most **12:1**. Client metadata is not a
   decoder verdict.
4. `ffmpeg` is invoked with fixed non-shell argv to select a server-derived
   time, extract one video frame, disable audio/subtitles/data, and scale it
   within **1,280 px** / **2 MP**. Browser-provided filters, destinations and
   executable paths are never accepted. Probe and render have bounded
   timeouts and a one-slot local execution gate covering private source copy,
   probe and render.
5. The candidate JPEG is opened and verified with Pillow, size-capped by
   `WEBAPP_VIDEO_OPERATIONS_MAX_OUTPUT_MB` (default **4 MiB**), hashed, then
   atomically promoted below a separate private Video Operations root. It is
   marked `completed` only after the final file is re-opened and re-verified.
6. `web_video_operations`, `web_video_operation_attempts`, and
   `web_video_operation_events` retain operation/attempt/lifecycle evidence.
   They are additive Web tables, not Bot job, wallet, provider, payment or
   Asset Vault source tables.

Every create requires a signed session, CSRF, owner check, server-side
idempotency key and request fingerprint. Reusing a key for another source or
poster position conflicts; a matching replay returns the original operation.
Only verified completed output counts toward the account Video Operations
quota (default **50 MiB**).

Downloads re-check owner, exact JPEG metadata, byte count and SHA-256 from a
pinned private descriptor, then seal and re-hash an ephemeral private delivery
copy before streaming it. This prevents a later write to the retained output
inode from changing bytes in an in-flight response. The temporary delivery copy
is deleted after the response; it is not a persistent output, public URL, CDN
object or PWA cache entry. Attachments send `no-store, private`, `nosniff`,
`no-referrer`, and CSP `sandbox`.

## Configuration and runtime readiness

All feature gates are false by default:

```text
WEBAPP_ASSET_VAULT_ENABLED=false
WEBAPP_VIDEO_OPERATIONS_ENABLED=false
WEBAPP_VIDEO_POSTER_ENABLED=false
WEBAPP_VIDEO_OPERATIONS_ROOT=
WEBAPP_VIDEO_OPERATIONS_MAX_OUTPUT_MB=4
WEBAPP_VIDEO_OPERATIONS_QUOTA_MB=50
WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=
WEBAPP_VIDEO_FFMPEG_BIN=
WEBAPP_VIDEO_FFPROBE_BIN=
```

Enabling Video Operations requires Asset Vault and an isolated private root.
In production that root must be an absolute child of the Web service persistent
volume and must not overlap Asset Vault, Project Packages, Document Operations,
Image Operations, or `static`.

Because this is a request-time SQLite executor rather than a distributed
worker, the operator must additionally set
`WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica`. For every enabled
runtime, one of `RAILWAY_REPLICA_COUNT`, `RAILWAY_REPLICAS`, or
`WEBAPP_REPLICA_COUNT` must also attest exactly `1`. Any missing, malformed or
multi-replica topology fails closed before a video source is opened.

The runtime additionally needs trusted `ffmpeg`, `ffprobe`, and Pillow. A
future, separately reviewed deployment change must install FFmpeg in the build
image (for the current Nixpacks deployment, this means an explicit package
configuration) before any Video Poster flags are enabled. This contract does
not install packages, change Railway, deploy, or permit a fallback to a
browser/provider/Bot renderer. An absent or invalid runtime fails closed with
a guarded/unavailable response.

## Operating model and explicit non-goals

This first slice uses a **bounded request-time executor**, not a durable queue
worker. Attempt and event rows provide auditability and a seam for a future
leased worker, but there is currently no worker process, retry daemon,
automatic repair, persistent queue lease or multi-replica coordination. The
single-replica topology gate blocks use in a multi-replica deployment; it is
not a distributed coordination mechanism. There is also no long-video/series
render service. Startup reconciliation fails interrupted work rather than
pretending it will resume.

It does not provide AI/video generation, edit, trim, transcoding, preview
player, long-form/multiscene production, background processing, provider
integration, Bot bridge calls, wallet/Xu pricing or charge, PayOS handling,
webhook, publish, notification, public share, or external delivery. Video
Studio remains a planning surface until separately upgraded through its own
engine and delivery contract.
