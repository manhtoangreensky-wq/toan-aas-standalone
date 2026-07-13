# Web-native Image to PDF contract

`/documents/image-to-pdf` is a bounded **Document Operations** capability
owned by the standalone Web App. It produces a new private PDF from selected
Asset Vault images; it is not a Bot job or an extension of the Telegram file
flow. It does not create, read or alter Telegram identity, Xu, PayOS,
provider state, wallet state, Bot asset delivery or Bot document records.

## Scope and lifecycle

- API: `POST /api/v1/document-operations/image-to-pdf`.
- Kind: `image_to_pdf`.
- The form exposes ordered slots **Ảnh 1 → Ảnh 8**. The submitted order is
  part of the request fingerprint and is exactly the page order in the
  generated PDF.
- A normal request transitions `queued → processing → completed`; malformed,
  unsafe or unavailable input becomes `failed` or `guarded`. The UI never
  presents a placeholder file as a completed output.
- A completed result exists only after every source and the generated PDF have
  passed the server-side validation described below.

## Input and output boundary

1. The browser submits one to eight distinct Asset Vault IDs and an
   idempotency key. It never submits image bytes, local paths, raw filesystem
   paths, storage keys, URLs, Telegram file IDs or provider handles.
2. Each source must be an active, owner-scoped, canonical JPEG, PNG or WebP
   Asset Vault asset. Server validation checks the allowed extension and MIME
   type, verifies the staged copy's SHA-256, and limits every source to
   **20 MiB** and all selected sources together to **40 MiB**.
3. Pillow decodes each source in isolated staging. It rejects unreadable
   images, empty or invalid dimensions, decoder/decompression-bomb warnings,
   decoder/decompression-bomb errors, animated or multi-frame images, a
   source with either side above **7,680 px**, an aspect ratio above **12:1**,
   a decoded raster above **16 MP (million pixels)**, or a source set above
   **32 MP** in total. Browser MIME claims, client previews and image metadata
   are never trusted as a decoder verdict.
4. The server normalizes each accepted raster into a safe still image and
   generates a fresh, one-page-per-source PDF. It uses `pypdf` to strictly
   reparse the candidate, confirm the expected page count, and verify final
   size and SHA-256 before publishing. It does not pass a browser file, image
   URL or source asset directly through as an output.
5. The verified artifact is atomically promoted into the Document Operations
   root, which is separate from Asset Vault, Project Packages and `/static`.
   Download is only an owner-scoped signed-session attachment endpoint with
   `no-store, private`, `nosniff`, `no-referrer` and `sandbox`; the PWA shell
   never caches document-operation responses or private files. A missing or
   tampered artifact becomes `unavailable`, not downloadable.

The operation row retains the first selected source only for compatibility.
The immutable `web_document_operation_sources` map is authoritative for the
complete ordered source set and its server-verified sizes and hashes. Those
details do not appear in browser responses or audit text.

## Configuration and request protection

Image to PDF is deliberately opt-in and requires the existing private
Document Operations boundary plus its own feature gate:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_IMAGE_TO_PDF_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

In production, all roots must be separate absolute children of the Web
service persistent volume. When Image to PDF is enabled, both Pillow and
`pypdf` are required; missing decoder/parser support or an invalid private
storage boundary fails closed rather than using a shell or public-file
fallback.

- Creation requires a signed session, CSRF validation, a bounded request and
  the Document Operations per-IP work gate. List, detail and download remain
  owner-scoped and non-enumerating.
- Idempotency binds the ordered source IDs and their server-verified
  SHA-256/byte-size values. The same intent returns one record; a different
  ordered source set under the same key is a conflict.
- The legacy generic `documents` and `documents_pdf` feature APIs explicitly
  reject `operation=image_to_pdf` before any bridge call. This prevents a
  crafted browser request from creating a second Bot/staging workflow; the
  only accepted creation route is this private Web-native operation.
- The build runs in a server thread pool so bounded raster/PDF work does not
  hold the async request loop. A process-wide capacity gate permits one active
  decoder-heavy Image to PDF batch per Web process; a concurrent request gets
  a truthful retry response before creating an operation row. The byte,
  source-count, dimension, aspect-ratio and pixel limits are enforced before
  a large decode or output is retained.
- Audit records contain only operation ID, source count, page count, output
  byte count and outcome—never a pathname, filename, asset ID, hash, image
  content, provider, payment or wallet field.

## Explicit non-goals

- No Bot bridge, Telegram upload, browser-to-provider request, provider call,
  command shell, FFmpeg path, webhook, PayOS callback, manual top-up or
  Xu/wallet/ledger mutation.
- No browser raw-file upload, arbitrary URL/local-path import, public preview,
  OCR, image editing/upscaling, PDF merge/split/translation, or implicit
  conversion of the result into a Bot asset.
- No acceptance of GIF, SVG, AVIF, HEIC, animated WebP or other unbounded
  image/container formats in this first private utility.
- No claim that the Bot's optional image-to-PDF helper is deployed, linked or
  authoritative for this separately secured Web-native output.
