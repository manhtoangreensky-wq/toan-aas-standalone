# Web-native PDF Optimize contract

`/documents/compress` is presented as **PDF Optimize** because this Web
capability refuses to promise a compression level that the implementation
cannot prove. It is a standalone Web artifact workflow, not a Bot job. It
does not create, read or alter Telegram identity, Xu, PayOS, provider state,
Bot asset delivery or the Bot's document records.

The audited Bot `/compress_pdf` helper uses an optional PyMuPDF save pass and
currently reports success without confirming that the result is smaller. The
Web contract deliberately improves that behavior: a completed result is only
possible after the final sanitized artifact is meaningfully smaller than the
verified source. The existing source is never replaced.

## Scope and truthfulness

- API: `POST /api/v1/document-operations/pdf-optimize`.
- Kind: `pdf_optimize`.
- Input: exactly one active, owner-scoped Asset Vault PDF.
- Normal lifecycle: `queued → processing → completed`.
- A terminal `guarded` state with `PDF_NOT_REDUCED` means there was no final
  safe artifact smaller enough to deliver. It has no storage key, no
  download, no saved-size claim and **does not change the source file**.
- The UI exposes one real structural optimization profile. It does not imitate the Bot's
  light/medium/strong labels because those labels currently do not select
  different engine behavior.

## Bounded private pipeline

1. The browser submits only an Asset Vault ID and an idempotency key. It never
   uploads PDF bytes, sends a local path, URL, storage key, Telegram file ID
   or provider handle.
2. The server owner-scopes the active canonical PDF, limits it to 20 MiB,
   copies and SHA-256-verifies it in isolated staging, strictly parses it and
   rejects encrypted/malformed PDFs or documents outside 1–30 pages.
3. A fresh `pypdf` writer copies page content, removes annotations,
   automatic actions and related interactive page metadata, applies
   `compress_content_streams(level=9)` (Flate content-stream compression) and
   removes duplicate/unreferenced writer objects. It does not resample image pixels, choose a lossy quality
   level, execute a PDF shell command or call a provider.
4. The candidate must fit output/account quotas, be strictly reparsed with the
   original page count, hash/size checked and be at least **1 KiB and 1%**
   smaller than the verified source. Otherwise the candidate is deleted and
   the operation becomes guarded; it is never called compressed.
5. Completed output is atomically promoted to the Document Operations root,
   separate from Asset Vault, Project Packages and `/static`. It is delivered
   only as a signed-session attachment with `no-store, private`, `nosniff`,
   `no-referrer` and `sandbox`. PWA shell caching never includes the API or
   private file. Tampering turns a completed output `unavailable`.

## Configuration and safeguards

PDF Optimize uses the existing opt-in Document Operations boundary:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

In production the roots must be separate absolute children of the Web service
persistent volume. Document Operations remains disabled by default. The pure
Python `pypdf` runtime is required when enabled; startup fails closed if it is
not installed.

- Signed session and CSRF are mandatory; list/detail/download remain
  owner-scoped and non-enumerating.
- Idempotency binds the source ID, verified SHA-256 and source byte size.
  Same intent replays one record; a different source under the same key is a
  conflict.
- The endpoint has the Document Operations per-IP parser gate before work.
- Audit contains only operation ID, page count, output bytes, saved bytes and
  outcome—never a PDF path, filename, hash, source ID, content, provider,
  payment or wallet field.
- The builder runs in the server thread pool so bounded PDF processing does
  not hold the async request loop. It is still deliberately capped; a future
  large/lossy optimizer must use an isolated resource-limited worker rather
  than a shell fallback.

## Explicit non-goals

- No lossy image recompression, conversion tier, OCR, translation, Ghostscript
  or qpdf shell invocation, provider call, Bot bridge, payment/webhook or Xu
  mutation.
- No public preview or source replacement.
- No claim that Bot compression availability or its success message proves a
  production Web output. This is an independently secured, verified Web
  utility.
