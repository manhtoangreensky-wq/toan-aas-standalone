# Private PDF OCR contract

## Purpose and Bot reference

`/documents/pdf-ocr` converts the useful bounded local behavior of the frozen
Telegram Bot's `/ocr_pdf` flow into an independent signed Web workflow: one
private PDF, at most 10 pages, rendered at 2× and read by local Tesseract.

It deliberately does **not** copy Telegram reply/pending-file state, Telegram
file IDs, document charges, Xu ledger entries, Bot job records, provider calls,
PayOS, webhooks or Telegram delivery. `bot.py` remains a read-only reference.

## Public surface

- Private page: `/documents/pdf-ocr`.
- Signed, CSRF-protected API: `POST /api/v1/document-operations/ocr-pdf`.
- Exact request schema: `{ "source_asset_id", "language" }`, with `language`
  restricted to `auto`, `vi`, or `en`.
- The browser cannot send a file, URL, path, page count, render scale, OCR
  command/options, provider/model, idempotency key or recognized text.

The server derives idempotency from the signed account, immutable Asset Vault
source hash/size, language, fixed 2× renderer and fixed OCR contract. A refresh
cannot create a second private output for the same source revision and mode.

## Explicit readiness

All of the following are required:

- `WEBAPP_ASSET_VAULT_ENABLED=true`
- `WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true`
- `WEBAPP_DOCUMENT_OCR_PDF_ENABLED=true`
- a separate persistent Document Operations root in production
- `pypdf`, `pypdfium2`, `pytesseract`, a local Tesseract binary and the needed
  local language pack (`vie` and/or `eng`)

The PDF OCR flag defaults to `false`, independently of image OCR and PDF →
images. Disabled access returns a fail-closed 503. Missing runtime or requested
language pack returns an honest `guarded` response without an artifact.

## Input and execution limits

Only an active owner-scoped Asset Vault PDF with canonical `.pdf` extension,
`application/pdf` type, valid hash and size from 1 byte through 20 MiB is
accepted. The server hash-copies it to isolated staging before parsing.

- Strict `pypdf` parsing rejects invalid and encrypted PDFs.
- Page count is 1–10, matching the useful Bot boundary.
- PDFium preflights every page at fixed 2×. Each page is limited to 8 MP and
  8,192 px on either axis; all pages total at most 48 MP.
- PDF rendering and decoded-image OCR share two process-wide fail-fast gates.
  A busy gate returns 429 before a lifecycle row or output is created.
- Tesseract has a 30-second per-page timeout and a 120-second total operation
  budget checked before/after parsing, PDFium rendering and OCR. The total
  clock starts before parsing; each Tesseract subprocess is given only its
  remaining global budget. A timeout is terminal (`failed`), never
  reclassified as temporary runtime readiness or replayed forever. Python
  cannot safely terminate a stuck native PDFium call in-place, so production
  may enable this flag only in a worker/container with an outer wall-time,
  CPU and memory limit. The server never falls back to browser OCR, a provider
  or the Bot.

## Truthful output and delivery

The output is a `.txt` artifact only when local OCR recognized real non-empty
text. Recognized pages have `=== Trang N ===` headers; blank pages are omitted
rather than receiving invented placeholders. If every page is blank, lifecycle
ends `guarded` with `WEB_DOCUMENT_OCR_TEXT_NOT_FOUND` and no TXT is offered.

Recognized text is normalized to valid UTF-8, bounded to 500,000 characters and
2 MiB, written to staging, re-read, hash-verified and atomically promoted to a
server-owned output key. Text never enters JSON, audit detail, browser state or
PWA cache.

Download is owner-scoped through the signed session. The server pins and hashes
the output descriptor, seals a rehashed anonymous stream before delivery, and
uses a canonical attachment filename/MIME with `no-store, private`, `nosniff`,
`no-referrer` and sandboxed content security policy. A missing, changed or
tampered artifact becomes `unavailable`; it is never served by pathname after a
prior check. Only two sealed Document Operation downloads may exist per Web
process; a third request fails fast with 429 before it consumes temporary disk.
The persistent Document Operations root must remain app-owned and inaccessible
for writes by users or local co-tenants; it is not a shared upload directory.

## Non-goals

- OCR accuracy, handwriting/layout/table/form reconstruction, translation,
  editable transcript, previewing OCR text in the browser, or preserving PDF
  visual layout.
- Remote OCR/provider requests, Core Bridge/Bot execution, Telegram delivery,
  jobs, Xu, payment, PayOS, webhooks, publishing or asset-publication flows.
