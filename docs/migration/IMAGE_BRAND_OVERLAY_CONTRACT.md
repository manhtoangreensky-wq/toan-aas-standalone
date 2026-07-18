# Web-native Brand Overlay Studio contract

`/image/brand-overlay` creates a new, private PNG that adds a short text
brand marker and/or a second private image as a logo. It carries the useful
local-image-editor semantics from `bot.py` into the standalone Web App, but
does not import Telegram conversation state, Bot file delivery, wallet logic
or provider execution.

It does not create, read or change Telegram identity, Xu, PayOS, provider
state, Bot jobs, Bot assets or webhook records.

## Lifecycle and owner boundary

- API: `POST /api/v1/image-operations/brand-overlay`.
- Reads: `GET /api/v1/image-operations?kind=image_brand_overlay`, operation
  detail and owner-scoped download.
- Kind: `image_brand_overlay`; this dedicated history is intentionally not
  mixed into the generic `/image/history` projection for Resize/Enhance.
- Normal lifecycle is `queued → processing → completed`. A PNG is completed
  only after it is re-opened, parsed, dimension-checked, hashed and atomically
  promoted into private Image Operations storage.
- Browser sends only owner-scoped Asset Vault IDs plus bounded choices. It
  never sends source/logo bytes, a URL, raw path, font path, canvas result or
  provider option. Both source and optional logo must be active JPEG, PNG or
  WebP assets of the signed Web account.

## Composition semantics

Text is server-normalized whitespace, limited to 260 characters and rendered
first; an optional logo is composited over it second. Each element has one of
nine fixed positions:

```text
top_left top_center top_right
center_left center center_right
bottom_left bottom_center bottom_right
```

The text uses a verified server Unicode font, wraps to a maximum of four lines
inside a rounded translucent dark block and never silently drops unrendered
words. If the image/text cannot fit safely, creation fails truthfully. Logo
sizes are limited to 12%, 18% or 22% of the canvas width, preserve aspect
ratio, and use an opacity from 25–100%. The server applies EXIF orientation,
flattens source transparency on white and preserves neither source metadata
nor client preview state in the output.

## Security, idempotency and storage

1. Source and logo are each hash-copied to isolated staging before Pillow sees
   their bytes. The server rechecks active state, byte length, digest and
   storage key before accepting the operation.
2. The idempotency fingerprint binds source ID/hash/size, optional logo
   ID/hash/size, normalized text digest, both positions, scale, opacity,
   renderer version and PNG output format. A changed request using an existing
   key conflicts; an exact replay remains available after original assets are
   archived.
3. The database stores only replay metadata for text (a digest, never raw text)
   and keeps logo ID/hash internal. Public operation responses expose only the
   safe boolean/position/scale/opacity projection.
4. The shared bounded Pillow decoder gate, source/output size limits, private
   quota, CSRF, signed session, owner checks, audit events and verified
   descriptor download are the same hardened Image Operations boundary used
   by Resize and Enhance.
5. Download remains `no-store, private`, `nosniff`, `no-referrer` and
   `sandbox`; there is no public preview URL, PWA private-file cache or
   browser-generated fallback.

## Configuration

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_IMAGE_OPERATIONS_ENABLED=true
WEBAPP_IMAGE_OPERATIONS_ROOT=/data/toanaas_webapp_image_operations
WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED=true
# Optional production pin; required only when text is used and the default
# verified DejaVu path is unavailable in the runtime.
WEBAPP_IMAGE_BRAND_OVERLAY_FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
```

The feature flag defaults to `false`. A configured font path is pinned
strictly; otherwise the pinned Pillow runtime's packaged Unicode font is the
deterministic fallback. Missing private storage or Pillow fails closed; it
never falls back to the Bot, browser canvas, a public file or provider call.
Logo-only requests do not need a text renderer.

## Non-goals

No watermark removal, generative edit, AI retouch, background removal,
provider call, Bot bridge, browser file/path import, video composition,
wallet/Xu mutation, PayOS action, webhook, public asset or fake output.
