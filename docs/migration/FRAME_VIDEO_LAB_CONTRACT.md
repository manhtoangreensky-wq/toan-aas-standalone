# Frame Video Lab — Web-native contract

## Purpose and scope

Frame Video Lab is a bounded, local Web App feature that converts an ordered
set of 2–8 images already owned by the signed account in Asset Vault into one
private MP4. It transfers only the useful Bot concept of an image-sequence
video. It does **not** transfer Telegram conversation state, mutable upload
paths, Local Worker hand-offs, Bot jobs, provider calls, wallet/Xu, PayOS,
notifications, social publishing, a browser-supplied FFmpeg command or a
claim that an AI-generated video was delivered.

The feature is disabled by default. A disabled/guarded runtime produces no
output and does not persist a fake success receipt.

## API

| Method | Route | Signed account / CSRF | Contract |
| --- | --- | --- | --- |
| `POST` | `/api/v1/frame-video-operations/estimate` | signed account | validates the current owner-scoped sources and returns a non-mutating plan |
| `POST` | `/api/v1/frame-video-operations` | signed account + CSRF | creates one immutable local operation from a closed request body |
| `GET` | `/api/v1/frame-video-operations` | signed account | lists only that account's opaque receipts |
| `GET` | `/api/v1/frame-video-operations/{id}` | signed account | reads a single owner-scoped receipt and lifecycle events |
| `GET` | `/api/v1/frame-video-operations/{id}/download` | signed account | verifies and seals the private MP4 before attachment delivery |

All normal responses retain the common `ok / status / message / data /
error_code` envelope. State is one of `queued`, `processing`, `completed`,
`failed`, `guarded` or `unavailable`. A generic Jobs/Assets projection uses
the separate opaque source `frame-video-operation`; it must never be routed as
the older single-video Poster source.

## Closed request and media policy

The body accepts only `source_asset_ids`, `aspect_ratio`,
`seconds_per_image`, `effect` and `idempotency_key` for creation. Extra
fields are rejected. Sources must be ordered, unique Asset Vault UUIDs with
active owner state, matching JPEG/PNG/WebP MIME/extension, a verified private
descriptor, at most 10 MiB each / 30 MiB total, one non-animated frame, no
more than 12 MP and safe geometry.

Accepted ratios are `9:16`, `16:9`, `1:1` and `4:5`; duration is 1.5, 3 or 4
seconds per image, capped at 24 seconds. Effects are `none`, `fade`, `zoom`,
`pan`, `slide` or deterministic `random`. Every input is normalized by Pillow
into server-owned staging. FFmpeg receives only a fixed list-argv command,
server-generated filter graph and server-generated private paths. It runs
with `shell=False`, a timeout, no audio/subtitles/data streams and no remote
protocol/URL input.

Only a file verified by ffprobe as one H.264 video stream, zero audio streams,
expected dimensions/duration, MP4 marker, byte limit and SHA-256 may become
`completed`. The output is verified once before and once after atomic private
publication. Browser download opens a descriptor with no-follow semantics,
rehashes it into an anonymous temporary sealed stream and releases its
capacity slot on every normal/error/client-disconnect exit path.

## Storage, schema and lifecycle

`WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT` is a distinct private root, outside
`static`, Asset Vault, package, document, image, subtitle and Poster video
roots. Production requires it below the Railway persistent volume. Additive
tables are:

- `web_frame_video_operations` — lifecycle/output receipt only;
- `web_frame_video_operation_sources` — ordered immutable source snapshot;
- `web_frame_video_operation_attempts` — fenced local execution attempt;
- `web_frame_video_operation_events` — append-only lifecycle timeline.

The account/kind/idempotency key is unique. Same key plus same ordered snapshot
and settings replays the existing receipt; a changed source order, asset hash,
duration, ratio or effect returns conflict. The Asset Vault lifecycle exposes
only an owner-scoped `frame_video_operation_source` reference count; it does
not leak source IDs, storage keys or digests in the Frame Video public view.

Deferred startup reconciliation marks only pre-readiness `queued` or
`processing` requests as `failed / FRAME_VIDEO_INTERRUPTED`, revalidates every
completed artifact and marks corrupt output `unavailable`, then removes only
old regular unreferenced files under this module's own staging/output
directories.

## Runtime, topology and flags

Required opt-in flags:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED=true
WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica
RAILWAY_REPLICA_COUNT=1
```

`WEBAPP_FRAME_VIDEO_FFMPEG_BIN` / `WEBAPP_FRAME_VIDEO_FFPROBE_BIN` may set
absolute reviewed binaries; the existing explicitly configured video binary
variables are only fallbacks. The feature shares one process-wide FFmpeg gate
with Video Poster and one Pillow decoder gate with image operations. A
multi-replica, missing attestation, invalid binary or missing persistent
boundary fails closed. Default local/production flags remain false, and this
contract authorizes neither providers nor payments.

## Verification evidence

`tests/test_copyfast_frame_video_operations.py` covers disabled defaults,
raw-body cap, topology guard, owner/CSRF isolation, duplicate/extra-field
rejection, fixed non-shell FFmpeg argv, deterministic idempotency, H.264/no-
audio receipt verification, sealed private download, tamper refusal, generic
opaque Jobs/Assets delivery and the shared Poster/Frame Video gate.
