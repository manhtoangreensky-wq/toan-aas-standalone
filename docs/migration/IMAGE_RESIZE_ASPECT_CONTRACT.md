# Web-native Resize & Aspect Studio contract

`/image/resize` is a bounded, deterministic **Image Operations** capability
owned by the standalone Web App. It takes one private Asset Vault image and
creates one new private PNG. It mirrors the useful local Telegram image tool
behaviour—center crop, white pad and blur background—without importing the
Bot's in-memory state, Telegram file flow or payment behaviour.

It does not create, read or alter Telegram identity, Xu, PayOS, provider
state, wallet state, Bot jobs, Bot asset delivery or webhook records.

## Scope and lifecycle

- API: `POST /api/v1/image-operations/resize`.
- Read APIs: `GET /api/v1/image-operations`, `GET /api/v1/image-operations/{id}`
  and owner-scoped `GET /api/v1/image-operations/{id}/download`.
- Kind: `image_resize`.
- Lifecycle is `queued → processing → completed`; unsafe, malformed or
  unavailable input becomes `failed` or `guarded`. A completed result exists
  only after the generated PNG has been reopened, checked and hashed.
- The source Asset Vault file stays immutable. This is deterministic LANCZOS
  interpolation, not AI upscale, retouch, subject recognition or a
  focal-point crop editor.

## Bot parity rendered as a Web-native contract

The Web controls use these canonical targets from the local image tool:

| Preset | Target pixels |
| --- | --- |
| `1:1` | 1024 × 1024 |
| `9:16` | 1080 × 1920 |
| `16:9` | 1920 × 1080 |
| `4:5` | 1080 × 1350 |
| `3:4` | 1080 × 1440 |
| `4:3` | 1440 × 1080 |
| `3:2` | 1500 × 1000 |
| `2:3` | 1000 × 1500 |
| `21:9` | 1920 × 823 |

Custom dimensions require both sides, each from 128 to 4096 px. The output is
limited to 16 MP and 12:1 aspect ratio; malformed input never silently falls
back to a square canvas.

- `crop`: deterministic **center crop in source coordinates**, then LANCZOS
  resize. It fills the canvas and can remove outer pixels without first
  allocating a giant cover-sized intermediate raster.
- `pad`: LANCZOS contain resize, centered on an opaque **white** canvas. It
  preserves the whole source without cropping.
- `blur`: a safely bounded cover background with Gaussian blur radius 28,
  then a centered unblurred contain image. It is not subject aware. Blur is
  behavioural parity, rather than a claim of pixel-identical output to the
  legacy Bot's unbounded cover implementation.

All modes emit an opaque fresh PNG. EXIF orientation is applied, then EXIF,
comments, ICC/source metadata and alpha are not propagated to output. The
source is never overwritten.

## Input, storage and delivery boundary

1. Browser submits only an Asset Vault ID, normalized preset/dimensions,
   mode and idempotency key. It never submits source bytes, path, storage key,
   URL, Telegram file ID or provider handle.
2. Source must be an active, owner-scoped JPEG, PNG or WebP with canonical
   extension/MIME. Server hash-copies it into isolated staging and repeats
   signature verification. It accepts at most **20 MiB**.
3. Pillow validates compressed bytes before full decode, rejects corrupted or
   truncated sources, decompression-bomb warnings/errors, animation/multiple
   frames, dimensions above **7,680 px**, aspect above **12:1**, and decoded
   source raster above **16 MP**.
4. Candidate PNG has a fresh storage key under `outputs/`, is capped by
   `WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB`, verified twice with Pillow,
   checked for expected PNG format, one frame, exact dimensions and no EXIF,
   hash-verified after atomic promotion, then marked `completed`.
5. `web_image_operations` and `web_image_operation_events` are independent
   from document operations. The private root is separate from Asset Vault,
   Project Package, Document Operations and `/static`.
6. Download derives MIME and attachment filename from the known operation
   kind, checks signed-session ownership and integrity again through the same
   opened file descriptor that is streamed to the customer (with no-follow on
   supported runtimes), and sends
   `no-store, private`, `nosniff`, `no-referrer` and `sandbox`. Missing,
   mutated or malformed output becomes `unavailable`; it is never served as a
   public file or PWA cache item.

## Configuration and request protection

The feature is deliberately opt-in:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_IMAGE_OPERATIONS_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_ROOT=/data/toanaas_webapp_image_operations
WEBAPP_IMAGE_RESIZE_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_IMAGE_OPERATIONS_QUOTA_MB=100
```

In production every private root must be an absolute, separate child of the
Web service persistent volume. Missing Pillow/runtime/storage configuration
fails closed rather than falling back to browser canvas, a public file, Bot
transfer or provider call.

- Creation needs signed session, CSRF, owner-scoped source check, idempotency,
  rate limit and a shared one-slot Pillow decoder gate. The gate is shared
  with Image → PDF, so two independent image pages cannot bypass the process
  memory limit. A busy new request returns 429 before a row or staging file is
  created; a matching replay remains readable before the gate.
- The request fingerprint contains source ID, source SHA-256/byte size,
  normalized preset, target pixels, fit mode and fixed PNG output contract.
  A key reused for different intent returns conflict. A matching replay keeps
  returning its original canonical record even after its source is archived;
  it never starts a new source read.
- On Web process startup, retained completed outputs are rechecked and
  tampered/missing files become `unavailable`. Because Resize Studio has no
  resumable worker, an interrupted `queued` or `processing` record becomes
  `failed` with an auditable terminal event rather than remaining stuck.
- Only verified `completed` artifacts count against the Image Operations
  quota. An `unavailable` artifact cannot permanently consume capacity after
  its private file has gone missing or failed integrity.
- Generic feature APIs explicitly reject `image_resize`, `resize` and
  `aspect_resize` before a bridge request. This prevents a crafted image form
  from creating a second Bot/provider lifecycle.
- Audit records contain only operation ID, normalized geometry/mode, source
  dimensions and output size. They never contain paths, filenames, asset IDs,
  hashes, image content, provider, payment or wallet fields.

## Explicit non-goals

- No Bot bridge, Telegram upload, browser-to-provider call, provider call,
  command shell, FFmpeg, webhook, PayOS callback, manual top-up or Xu/wallet
  mutation.
- No public preview URL, browser-side rendering/output, raw file/path import,
  GIF/SVG/AVIF/HEIC/animated WebP, background removal or real AI upscale.
- No promise that the Telegram Bot's guarded AI enhancement routes are now
  enabled in Web. Those remain separate canonical workflows until a reviewed
  engine contract exists.
