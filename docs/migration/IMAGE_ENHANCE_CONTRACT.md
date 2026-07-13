# Web-native Image Enhance Studio contract

`/image/edit` is a bounded, deterministic **Image Operations** capability
owned by the standalone Web App. It takes one private Asset Vault image and
creates one fresh private PNG. The renderer carries the useful local Telegram
image-editor presets into a Web-native, owner-scoped workflow; it does not
copy Telegram conversation state, Telegram file delivery, wallet logic or
provider execution into the Web App.

It does not create, read or alter Telegram identity, Xu, PayOS, provider
state, wallet state, Bot jobs, Bot asset delivery or webhook records.

## Scope and lifecycle

- API: `POST /api/v1/image-operations/enhance`.
- Read APIs: `GET /api/v1/image-operations?kind=image_enhance`,
  `GET /api/v1/image-operations/{id}` and owner-scoped
  `GET /api/v1/image-operations/{id}/download`.
- Kind: `image_enhance`.
- A normal request transitions `queued → processing → completed`; malformed,
  unavailable or unsafe input becomes `failed` or `guarded`. An interrupted
  in-process record becomes `failed` on startup reconciliation. A missing or
  tampered retained output becomes `unavailable`, never a fake success.
- A completed result exists only after a fresh PNG is reopened, verified for
  expected dimensions/format, hashed and atomically promoted into the private
  Image Operations root. The Asset Vault source remains immutable.

## Bot parity rendered as a Web-native contract

The feature follows the local Bot editor's deterministic, non-AI colour and
detail treatment. It makes no pixel-identical claim for unbounded Telegram
inputs; the Web applies its stricter source and output safety limits first.

| Preset | Brightness | Contrast | Saturation | Sharpness | Tone |
| --- | ---: | ---: | ---: | ---: | --- |
| `photo_clear_detail` | 1.03 | 1.10 | 1.05 | 1.30 | `neutral` |
| `product_clean` | 1.08 | 1.08 | 1.02 | 1.22 | `clean` |
| `cinematic_warm` | 0.99 | 1.14 | 1.08 | 1.12 | `warm` |
| `fresh_blue` | 1.03 | 1.08 | 1.12 | 1.16 | `cool` |
| `food_vivid` | 1.04 | 1.12 | 1.24 | 1.25 | `warm` |

`custom` is explicit: brightness, contrast, saturation and sharpness must
all be supplied, each from **0.50 to 2.00**, with one of `neutral`, `warm`,
`cool` or `clean`. A named preset rejects client-supplied overrides, so a
browser cannot make ambiguous or unrecorded adjustments.

For every accepted still image, the server applies this fixed order:

1. Verify compressed bytes and image type, apply EXIF orientation, flatten
   transparency onto opaque white, and remove source metadata from the fresh
   output.
2. Apply autocontrast (cutoff 1), then brightness, contrast, saturation and
   sharpness in that order.
3. Apply the selected neutral/warm/cool/clean tone overlay.
4. If output geometry changes, use LANCZOS resize. If `basic_upscale=true`,
   apply the bounded local UnsharpMask pass after resize.

`basic_upscale` is only deterministic interpolation plus sharpening. It can
request at most **2×** enlargement and is capped at **4,096 px per side** and
**16 MP**; a large source is deterministically reduced to that same output
ceiling even when upscale is off. It does not invent detail, perform AI
upscale, remove backgrounds, remove objects, infer a subject, retouch a face
or call an AI/provider service.

## Input, storage and delivery boundary

1. Browser submits only an Asset Vault ID, a named preset or complete custom
   settings, the basic-upscale choice and an idempotency key. It never submits
   source bytes, a filesystem path, storage key, URL, Telegram file ID or
   provider handle.
2. Source must be an active, owner-scoped JPEG, PNG or WebP with canonical
   extension/MIME. The server hash-copies it to isolated staging and repeats
   signature verification. It accepts at most **20 MiB**. A staging-volume
   failure is a processing-boundary error and never marks a valid Asset Vault
   source unavailable; only source integrity/read evidence can do that.
3. Pillow rejects corrupt/truncated sources, decompression-bomb
   warnings/errors, animation/multiple frames, sides above **7,680 px**,
   aspect ratio above **12:1**, and decoded source raster above **16 MP**.
4. The candidate is a new opaque PNG under `outputs/`, capped by
   `WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB`, parsed and hash-checked before
   and after atomic promotion. Browser MIME claims and client preview state
   are not a decoder verdict.
5. `web_image_operations` and `web_image_operation_events` retain only
   canonical server-normalized settings (`settings_json`) plus lifecycle
   evidence. They remain independent from Document Operations, Bot jobs and
   wallet/ledger tables. The private root is separate from Asset Vault,
   Project Package, Document Operations and `/static`.
6. Download derives the PNG MIME/attachment name from the known operation
   kind, rechecks signed-session ownership and integrity through the same
   opened file descriptor it streams, and sends `no-store, private`,
   `nosniff`, `no-referrer` and `sandbox`. There is no public preview URL or
   PWA private-file cache.

## Configuration and request protection

The feature is deliberately opt-in:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_IMAGE_OPERATIONS_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_ROOT=/data/toanaas_webapp_image_operations
WEBAPP_IMAGE_ENHANCE_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_IMAGE_OPERATIONS_QUOTA_MB=100
```

In production, every private root is an absolute, separate child of the Web
service persistent volume. Missing Pillow/runtime/storage configuration fails
closed rather than falling back to browser canvas, a public file, Bot transfer
or provider call.

- Creation requires signed session, CSRF, owner-scoped source lookup,
  idempotency, rate limit and the shared one-slot Pillow decoder gate. A busy
  request returns 429 before an operation row or staging file is created;
  matching idempotent replays remain readable before the gate.
- The request fingerprint binds source ID, server-verified source SHA-256 and
  byte size, normalized preset/settings, basic-upscale choice and fixed PNG
  output. Reusing a key for another intent conflicts; a matching replay keeps
  its original canonical record even after the source is archived.
- Only verified `completed` artifacts count against the Image Operations
  quota. An `unavailable` artifact cannot retain quota after integrity fails.
- Generic feature APIs explicitly route `image_edit` to this native surface
  and reject a second bridge/provider lifecycle. The only accepted creation
  path is the private Image Operations endpoint above.
- Audit records contain operation ID, preset/upscale flag, server-derived
  geometry and output byte count only. They never contain a source path,
  filename, asset ID, hash, image content, provider, payment or wallet field.

## Explicit non-goals

- No Bot bridge, Telegram upload, browser-to-provider call, provider call,
  command shell, FFmpeg, webhook, PayOS callback, manual top-up or
  Xu/wallet/ledger mutation.
- No browser-generated output, public preview URL, raw file/path import,
  GIF/SVG/AVIF/HEIC/animated WebP, AI image edit, generative fill,
  background/object removal, face retouch or real AI upscale.
- No claim that Bot guarded/provider-backed image workflows are now enabled
  in Web. Those remain independent features until a reviewed engine contract
  exists.
