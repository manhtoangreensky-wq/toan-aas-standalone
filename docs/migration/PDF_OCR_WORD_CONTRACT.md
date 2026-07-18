# Private scanned PDF OCR to Word contract

## Purpose and boundary

`/documents/pdf-ocr-to-word` turns one bounded, private scanned PDF into one
new private DOCX **only** after local OCR has found real text and the DOCX has
passed structural and content verification. It carries forward the useful
local OCR boundary of the frozen Telegram Bot's `/ocr_pdf` reference, then
uses the Web-owned DOCX verification boundary. It is deliberately a separate
Web-native operation, not a change to `/documents/pdf-to-word`.

`/documents/pdf-to-word` remains a text-extraction-only route. A scan never
silently gains OCR through that route, and a scan with no recognized text never
receives a blank, placeholder or fabricated DOCX.

The feature does not import Telegram file IDs/reply state, call or modify the
Bot, create a Bot job, call a provider, charge Xu, write a wallet, create or
finalize PayOS payment/webhook data, or claim Telegram delivery. `bot.py` is
read-only reference material only.

## Public surface and closed request

- Private customer page: `/documents/pdf-ocr-to-word`.
- Signed, CSRF-protected API: `POST /api/v1/document-operations/pdf-ocr-to-word`.
- Exact browser JSON schema: `{ "source_asset_id", "language" }`.
  `source_asset_id` must be one Asset Vault UUID owned by the signed account;
  `language` is only `auto`, `vi`, or `en`.
- Extra keys are rejected. The browser cannot provide bytes, a path, URL,
  source hash, output filename/MIME, page range/count, render scale, OCR
  command/options, Tesseract model, idempotency key, provider, Bot action or
  raw OCR text.

The server derives replay identity from the signed account, immutable source
asset/hash/size, selected language, fixed 2× renderer and fixed local OCR/DOCX
contract. Refreshing the same source revision and language returns the same
owner-scoped lifecycle result rather than creating another private output.

## Explicit readiness

All of these private boundaries must be intentionally enabled:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_PDF_OCR_WORD_ENABLED=true
WEBAPP_DOCUMENT_OCR_PDF_ENABLED=true
WEBAPP_PDF_TO_WORD_ENABLED=true
```

Asset Vault and Document Operations require their separate app-owned,
persistent roots in production. The feature also requires `pypdf`,
`pypdfium2`, `pytesseract`, local Tesseract with the requested local `vie`
and/or `eng` language pack, and `python-docx`. Every feature flag defaults to
`false` where applicable; any disabled prerequisite returns fail-closed 503.
Missing local OCR runtime or language produces an honest guarded response and
no artifact.

## Source, resource and timeout limits

Only an active owner-scoped Asset Vault PDF with canonical `.pdf`,
`application/pdf`, an intact source hash and a size from 1 byte through 20 MiB
is accepted. The server copies and verifies the source into isolated staging
before it parses or renders it.

- Strict `pypdf` parsing rejects malformed and encrypted PDFs.
- The source has 1–10 pages. PDFium preflights each page at a fixed 2× scale.
- Each rendered page is limited to 8 MP and 8,192 pixels on either axis; the
  entire operation is capped at 48 MP.
- OCR text is bounded at 500,000 recognized characters before DOCX creation;
  DOCX export then applies the stricter 250,000-character and 10,000-paragraph
  ceiling. DOCX archive/output verification also obeys the configured private
  Document Operations output quota.
- The route atomically reserves the shared PDF-raster, local-image-OCR and
  DOCX-writer capacity gates. A busy gate returns 429 before a new lifecycle
  row or output is created.
- Tesseract receives at most 30 seconds per page and only the remaining part
  of a 120-second whole-operation budget. Timeout is terminal `failed`, not a
  temporary readiness condition or an endless replay.

The 120-second deadline is a **soft in-process boundary** around Python and
Tesseract. Python cannot safely hard-kill an in-process native PDFium/Pillow
call. Production may enable this flag only inside a worker/container with an
outer wall-time, CPU and memory limit. The Web App never compensates with
browser OCR, remote OCR, a provider or the Bot.

## Truthful DOCX and private delivery

Only real, normalized local OCR fragments become DOCX paragraphs. Recognized
pages retain `=== Trang N ===` markers; blank pages are omitted. If every page
is blank, the lifecycle becomes `guarded` with
`WEB_DOCUMENT_OCR_TEXT_NOT_FOUND`; no DOCX, preview text or download link is
created. OCR is logical text extraction, not a promise to preserve a scan's
layout, handwriting, tables, images, fonts or form fields.

`python-docx` creates a fresh DOCX in private staging. Before atomic promotion,
the service bounds and inspects its ZIP structure, rejects traversal/symlinks,
encryption, macros, ActiveX, embedded payloads and external relationships,
requires essential OOXML parts, reopens it with `python-docx`, and checks its
visible paragraphs against the recognized text. It then rehashes the artifact
after promotion. A missing, changed, corrupt or tampered output becomes
unavailable and is never served as a file path.

The document is downloadable only by the same signed owner. Download pins and
hashes the descriptor, seals a rehashed anonymous stream before delivery and
uses canonical attachment MIME/name with private `no-store`, `nosniff`,
`no-referrer` and sandboxed CSP headers. OCR text is absent from JSON envelopes,
audit detail, browser state and the PWA cache. The private operations root is
not a shared upload directory and must not be writable by users or local
co-tenants.

## States and non-goals

The normal lifecycle is `queued → processing → completed`; guarded outcomes
preserve the absence of a deliverable, while input integrity, parser, renderer,
timeout and output-verification faults are recorded as failed without an
artifact. Capacity is refused with 429 before a new lifecycle row or output is
created. The result is not an approval, translation,
preview, editing workflow, public upload, provider task, Bot job, payment,
wallet action, PayOS action, webhook, asset-publication flow or notification.

No browser OCR, remote OCR/provider request, Core Bridge/Bot execution,
Telegram delivery, Xu, wallet, jobs, PayOS, payment, webhooks or raw OCR text
is part of this contract.
