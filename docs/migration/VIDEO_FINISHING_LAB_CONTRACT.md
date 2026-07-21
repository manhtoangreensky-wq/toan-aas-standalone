# Video Finishing Lab — Web-native contract

## Purpose and boundary

Video Finishing Lab is a bounded, private Web App utility that carries forward
the useful local Video Editor concept from the frozen Telegram Bot: reframe a
single owned video, apply a small visual preset and optionally preserve its
first audio track. It is deliberately not a replacement for Video Studio,
Telegram conversations, Bot jobs, local-worker orchestration, provider-backed
video generation, wallet/Xu, PayOS, publishing, text/watermark composition or
add-music functionality.

The browser never provides a filesystem path, URL, FFmpeg command, filter
graph, crop coordinate, subtitle, text, font, audio file, provider handle or
output location.

## Routes

All routes require the signed Web session. Mutating creation requires CSRF.

| Route | Meaning |
| --- | --- |
| `POST /api/v1/video-transform-operations/estimate` | Validates the owner-scoped source reference and closed plan without creating a receipt or file. |
| `POST /api/v1/video-transform-operations` | Creates one idempotent, verified private MP4 receipt. |
| `GET /api/v1/video-transform-operations` | Lists only the signed owner's receipts. |
| `GET /api/v1/video-transform-operations/{id}` | Returns only that owner's safe status/events. |
| `GET /api/v1/video-transform-operations/{id}/download` | Re-verifies and seals the owner's private MP4 before delivery. |

The generic opaque Jobs/Assets route can dispatch to the same verified
download, but never exposes the internal operation or Asset Vault ID.

## Closed input and limits

The source must be one active Asset Vault `video/mp4` with an immutable hash,
maximum 25 MiB, duration 0.2–60 seconds, max 4096 pixels per side, 16 MP,
12:1 aspect and 1–60 FPS. The input can contain exactly one video stream and
at most one audio stream. Supported video codecs are H.264, HEVC, VP8 and
VP9; audio preservation accepts only a bounded safe allowlist and transcodes
to AAC.

```json
{
  "source_asset_id": "uuid",
  "target_ratio": "9:16 | 16:9 | 1:1 | 4:5",
  "fit_mode": "crop | blur_pad",
  "preset": "none | clear | tiktok_pop | cinematic | soft_clean",
  "sharpen": true,
  "preserve_audio": true,
  "idempotency_key": "12–160 character safe token"
}
```

Output dimensions are server-owned, even and capped below 1.6 MP. `blur_pad`
uses a generated blurred cover background; it is not a disguised plain pad.
No custom filter or media source may be interpolated into the output command.

## Execution and verification

- The capability is false by default: `WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED=false`.
- Runtime requires `WEBAPP_ASSET_VAULT_ENABLED=true`, isolated private output
  storage, a validated FFmpeg/ffprobe binary and an explicit single-replica
  SQLite topology attestation.
- Video Poster, Frame Video and Video Finishing share one process-wide FFmpeg
  capacity gate. This prevents request bursts from starting parallel media
  parsers/renderers in the same process.
- Source bytes are descriptor-pinned, copied and SHA-256-checked before any
  parser opens them. The current source snapshot is checked again inside the
  receipt transaction.
- FFmpeg receives a fixed argv with `shell=False`, disabled stdin, no network
  protocol, fixed H.264/AAC output, stripped metadata/chapters/subtitle/data
  streams, output duration cap and a timeout.
- FFprobe verifies output MP4 magic, SHA-256, size, one H.264 `yuv420p` video
  stream at the requested dimensions/30 FPS, optional one AAC stream only,
  and a source-matched duration (with at most 0.5 seconds of container/frame
  tolerance). Verification happens before and after atomic
  private promotion.
- A receipt changes to `completed` only after both verifications pass. Runtime
  failure, quota failure or interruption becomes `failed`; output tampering or
  corruption becomes `unavailable`. The feature never fabricates success.

## Private storage and download

Output storage is separate from Asset Vault, documents, image operations,
Video Poster, Frame Video, packages and Bot state. Database records contain
only opaque IDs, source hash/size/type snapshot, closed spec, output receipt,
events and audit facts—never source/output paths, URLs, raw filters, provider
state, wallet/Xu or payment data.

Downloads first pin/hash the output descriptor with no-follow semantics,
copy/re-hash it into an anonymous temporary file, and stream that sealed copy
with `no-store`, `no-referrer`, `nosniff`, `sandbox` and same-origin resource
headers. Ownership is checked before every direct or generic download.

## Signed Portal handoff

`/video/finishing` is a dedicated signed customer workspace. It is deliberately
not a new item in the broad Video menu/catalog: its direct URL gives existing
Asset Vault customers a narrow, reviewable utility while the wider Video
navigation remains a separate migration task.

- The only source picker query is the server-owned
  `GET /api/v1/asset-vault?state=active&reference_kind=video_transform`.
  This exact reference kind returns only canonical active `.mp4` /
  `video/mp4` metadata belonging to the signed account; the Portal never
  downloads a general Asset Vault page and infers a usable video in the
  browser.
- The Portal holds source selection, closed settings, estimate and receipt
  state only in its current signed tab. It uses `no-store`, session/route
  fences and clears projections on failure, account change or route exit. No
  source ID, file metadata, receipt or setting is written to browser storage
  or the PWA cache.
- Changing the selected source or any closed setting invalidates a prior
  estimate. Creation requires a visible confirmation, CSRF and one body
  idempotency key. Ambiguous browser/network handling keeps that same key
  until a validated receipt and owner-scoped refresh settle; it must never
  silently create a second render.
- A download control appears only for a strict `completed` receipt with a
  verified MP4 output descriptor. The browser rejects a JSON envelope or an
  attachment missing `no-store`, `nosniff`, `no-referrer`, same-origin
  resource policy, attachment disposition or the expected byte size.
- Flag/runtime/topology/capacity errors stay visibly `guarded` or `failed`.
  The Portal does not claim a progress percentage, output, preview or retry
  before the server's receipt proves it. It does not change flags, runtime,
  topology, provider configuration or deployment.

## Explicitly deferred

Text/watermark overlays, custom crop/focal points, subtitle burn-in, music or
voice mux, AI upscale, remote providers, Bot/worker hand-off, billing and
publishing require separate contracts. They must not be added by widening this
request schema or accepting a raw FFmpeg fragment.
