# Web-native PDF text to Word contract

`/documents/pdf-to-word` is a bounded **Document Operations** capability
owned by the standalone Web App. It is a logical text export from one private,
text-bearing PDF to one new private DOCX attachment. It mirrors the useful Bot
`/pdf_to_word` boundary while deliberately improving source ownership,
idempotency, output verification and resource limits.

It is **not** OCR, a visual/layout conversion service, a table/image/font
preservation promise, a Bot job, or a provider integration. A scanned PDF or a
PDF with no text the parser can read has a truthful guarded outcome and never
receives a blank or fabricated DOCX.

## Scope and lifecycle

- Customer page: `/documents/pdf-to-word`.
- API: `POST /api/v1/document-operations/pdf-to-word`.
- Kind: `pdf_to_word_text`.
- Input: exactly one active, owner-scoped Asset Vault file with both `.pdf` and
  `application/pdf`, bounded to 20 MiB.
- Output: a newly generated
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  attachment. The server controls its storage key, MIME and download name; the
  browser never supplies a path, URL, source bytes, output name or MIME.
- States are `queued → processing → completed`, with `guarded` for
  `PDF_TEXT_NOT_FOUND`. Parse, integrity, resource and output failures are
  recorded as failed without an artifact.
- `source_page_count` is the verified PDF page count. DOCX pagination depends
  on the reader and is deliberately not presented as an invented page count.

## Real text only

The service parses a copied, hash-verified PDF using `pypdf` with strict mode.
It rejects encrypted/malformed input, more than 30 pages, and source integrity
changes. Each PDF page is text-extracted in the bounded worker path; the output
contains only sanitized logical text paragraphs. It never imports source PDF
annotations, attachments, actions, links, metadata, images, font programs,
macros or layout objects.

No OCR fallback exists. When every page has no usable extracted text the row is
set to `guarded` with `PDF_TEXT_NOT_FOUND`, the original Asset Vault PDF stays
active, and no DOCX/download URL is created. This is the same honest outcome
for a scan or image-only PDF even if a future OCR feature exists elsewhere.

## Resource and artifact safeguards

- The PDF uses the existing 20 MiB and 1–30 page limits.
- Text is bounded to 25,000 sanitized characters per page, 250,000 total
  characters and 10,000 output paragraphs.
- One PDF-to-Word process-wide slot is reserved only after owner/idempotency
  lookup; a new concurrent request returns 429 without a database row. A
  completed or guarded replay remains readable while that slot is busy.
- `python-docx==1.2.0` creates a fresh DOCX only after extraction. The output
  is not a copied PDF container or an external converter result.
- Before atomic promotion, the DOCX is checked as a bounded ZIP: no traversal,
  symlink, encryption, macro, ActiveX, embedded payload or external
  relationship; required OOXML parts must exist. It is reopened with
  `python-docx` and its visible paragraphs must match the extracted text.
- Size/hash are checked again after `os.replace` into the separate private
  Document Operations root. A corrupt/missing output becomes `unavailable`,
  never a downloadable attachment.

## Configuration and request protection

The service stays fail-closed unless all private boundaries are intentionally
configured:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_PDF_TO_WORD_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

`WEBAPP_PDF_TO_WORD_ENABLED` defaults to `false` and is independent from the
base Document Operations flag. Startup verifies `pypdf`; the DOCX runtime is
loaded only when this dedicated gate is enabled. The API requires signed
session ownership and CSRF for writes, validates an idempotency key against the
exact source asset/hash/size, has the Web document-operation request gate, and
emits a redacted Web audit event. The output download requires the same signed
owner, uses attachment-only `no-store`/`nosniff`/sandbox headers, and never
trusts a mutable database filename or MIME value.

## Independence and non-goals

No Bot bridge, Telegram identity, Xu ledger, PayOS order/webhook, provider,
browser-to-provider call, public/static output, external shell command,
LibreOffice, `pdf2docx`, or OCR engine is used. This module does not alter the
Telegram Bot or its payment/provider behavior.

## Test evidence required for a release

The Web tests cover real known-text PDF → reopened DOCX, CSRF/session and
owner isolation, scoped history, idempotent replay/conflict, encrypted/blank/
oversize-page/tampered/text-limit inputs, guarded no-text behavior, bounded
capacity, private download headers/MIME, output tamper handling, disabled flag,
and static UI/bridge-separation contracts. Full local tests, syntax checks and
`git diff --check` must pass before a PR is opened.
