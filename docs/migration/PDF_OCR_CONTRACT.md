# Private PDF OCR contract

## Purpose and Bot reference

`POST /api/v1/document-operations/ocr-pdf` carries the useful local OCR branch
of the frozen Telegram Bot command `/ocr_pdf` (`cmd_ocr_pdf`, `bot.py:128668`)
into a signed standalone Web account. It is an independent Web-native
Document Operations capability, not a copy of Telegram pending-file state,
file IDs, Bot jobs, Xu charging, PayOS or provider execution.

The API core is deliberately separate from Document Workspace authoring and
from the existing image-OCR page. A later UI pass may expose it as its own
Document Studio workflow; it must not silently turn an image-OCR action into
a PDF request or auto-run from a Workspace plan.

## Public boundary and lifecycle

- API: `POST /api/v1/document-operations/ocr-pdf`.
- Kind: `pdf_ocr`.
- Request is exactly `{ "source_asset_id", "language" }`; `language` is
  `auto`, `vi`, or `en`.
- Input is one active owner-scoped Asset Vault `.pdf` with canonical
  `application/pdf`, maximum 20 MiB.
- The operation receives every source page as one immutable unit and allows
  1–5 pages only. There is no browser page range, raw upload, URL, path,
  model/provider selector or client idempotency key.
- A server-derived receipt binds the signed account, Asset Vault ID, source
  hash/size, language and renderer version. Exact retries return the same
  owner-scoped receipt; a completed receipt remains replayable after a source
  is archived and even if the optional OCR runtime later becomes unavailable.
- States are `queued → processing → completed`, `guarded`, `failed`, and
  `unavailable`. A completed TXT exists only after every PDF page produced
  non-empty verified text. No partial/placeholder TXT is delivered.

## Runtime, bounds and isolation

The feature is independently opt-in through
`WEBAPP_DOCUMENT_OCR_PDF_ENABLED=true`, in addition to Asset Vault and base
Document Operations. It uses only local `pypdf`, PDFium (`pypdfium2`), Pillow
and Tesseract through `pytesseract`; no network request, Bot/Core Bridge,
provider call, shell converter, wallet, payment or webhook occurs.

Before a lifecycle is created, the server checks all optional local runtimes
and the requested `vie`/`eng` language pack. Missing readiness returns the
honest guarded response `WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE` or
`WEB_DOCUMENT_OCR_LANGUAGE_UNAVAILABLE`, with no job or output. A runtime
that disappears after preflight produces a guarded receipt, never a fake
success.

The source is copied into isolated staging only after owner, byte/hash and
storage-key checks. Strict `pypdf` parsing rejects encrypted or malformed
PDFs before rendering. PDFium then renders at fixed 2× scale under a shared
single renderer slot and the shared decoded-image slot. Limits are 4 MP per
page, 20 MP total, 15 seconds per local Tesseract page, 500,000 normalized
characters and 2 MiB UTF-8 output. A second request that cannot reserve both
slots receives 429 before creating a row.

## Output and delivery

For a successful request the server creates one UTF-8 `text/plain` attachment
named `toan-aas-pdf-ocr.txt`. It contains server-generated page separators
and normalized recognized text only. The temporary PNGs are deleted; raw OCR
text is never put in JSON, audit details, browser state, public URLs or PWA
cache.

The TXT is re-read, strict UTF-8 decoded, byte-counted and SHA-256 verified
before atomic promotion under the separate Document Operations root. Generic
owner-scoped Document Operations history/detail/download endpoints enforce
signed ownership and serve it with `Content-Disposition`, `Cache-Control:
no-store, private`, `nosniff`, `no-referrer` and CSP sandbox headers. A
tampered or missing committed file becomes unavailable fail-closed.

## Configuration and release evidence

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_DOCUMENT_OCR_PDF_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

`WEBAPP_DOCUMENT_OCR_PDF_ENABLED` defaults to `false`. It must use the same
persistent private-volume policy as Asset Vault and Document Operations; the
feature is guarded rather than falling back to ephemeral, browser or Bot
storage.

Release evidence covers strict request validation, CSRF, owner isolation,
hash-verified source copying, renderer/decoder capacity, page/pixel bounds,
empty text, optional-runtime preflight and race guards, replay without a
runtime, private attachment headers, audit redaction, output tampering and no
provider/payment/Bot leakage.
