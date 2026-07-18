# Private Image OCR contract

## Purpose and Bot reference

`/documents/ocr` carries the useful local OCR branch of the frozen Telegram
Bot's Document Tools flow (`bot.py:85114+`) into a signed Web account.  It is
not a copy of Telegram pending-file state, Telegram file IDs, document costs,
Xu charging, Bot jobs, or provider execution.

The first image-OCR scope is deliberately one private still image only. PDF
OCR is now covered by the separate bounded
[`PDF_OCR_CONTRACT.md`](PDF_OCR_CONTRACT.md); document translation remains
separate future work. This image-only surface must never imply a PDF workflow.

## Public surface

- Private route: `/documents/ocr`.
- Signed, CSRF-protected API: `POST /api/v1/document-operations/ocr-image`.
- Request is exactly `{ "source_asset_id", "language" }`, where `language`
  is `auto`, `vi`, or `en`.
- The browser never uploads OCR bytes, sends a URL/path/Telegram ID, chooses a
  provider/model, supplies an idempotency key, or receives recognized text in
  JSON.

The server derives replay protection from the signed account, the immutable
Asset Vault source revision, and public language choice. A refresh therefore
cannot create duplicate OCR artifacts for the same source revision.

## Preconditions and readiness

All of the following are explicit:

- `WEBAPP_ASSET_VAULT_ENABLED=true`
- `WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true`
- `WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED=true`
- an isolated Document Operations root on persistent storage in production
- a local Tesseract binary, `pytesseract` adapter, and a matching local
  language pack (`vie` and/or `eng`)

The OCR flag defaults to false. A disabled feature returns a fail-closed 503.
When the optional local runtime or requested language pack is missing, the API
returns a `guarded` response (`WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE` or
`WEB_DOCUMENT_OCR_LANGUAGE_UNAVAILABLE`) and creates no output or fake text.

## Input and execution boundary

Only one active JPEG, PNG, or WebP Asset Vault record owned by the current
signed Web account is accepted. The source is copied to a private staging
directory and its byte count, SHA-256, signature, decoder format, frame count,
dimensions, aspect ratio and 16 MP pixel budget are checked again.

OCR shares the process-wide decoded-image semaphore with Image to PDF and
Image Operations; only one decoder-heavy request can run per process. The
server applies a fixed local Tesseract configuration and timeout. There is no
browser OCR, remote URL fetch, provider/Core Bridge request, Bot call, job,
wallet mutation, PayOS action, or publish action.

## Output and delivery

Only non-empty recognized text is normalized into bounded UTF-8 and written
to an isolated private `.txt` artifact. The artifact is re-read, UTF-8
validated, SHA-256 verified, and stored under the server-owned Document
Operations output root before its operation becomes `completed`.

The API returns existing owner-scoped operation metadata only. Download uses
the signed session, `Content-Disposition: attachment`, `no-store, private`,
`nosniff`, and a server-owned `.txt` MIME/filename; it never exposes a storage
key, filesystem path, source hash, public URL, or OCR text preview.

If the image contains no readable text, the lifecycle is `guarded` with
`WEB_DOCUMENT_OCR_TEXT_NOT_FOUND`; no empty or invented text file is offered.

## Non-goals

- OCR over multiple pages, image translation, document translation, handwriting
  accuracy guarantees, layout reconstruction, table extraction,
  form filling, or transcription editing.
- Any third-party OCR/provider request, remote media lookup, Bot bridge,
  Telegram delivery, job queue, Xu ledger, PayOS/payment, or asset publishing.
- Any claim that a locally installed Tesseract language pack is present until
  the guarded readiness check has passed.
