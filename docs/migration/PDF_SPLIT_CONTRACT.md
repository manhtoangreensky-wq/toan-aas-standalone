# Web-native PDF Split contract

`/documents/split` is the first bounded **Document Operations** capability
owned by the standalone Web App. It mirrors the useful PDF Split bounds in the
frozen Bot baseline, but it is intentionally a separate Web artifact pipeline.
It does not create, read or alter a Bot job, Telegram identity, Xu ledger,
PayOS order/webhook, provider request or Bot asset delivery.

## Scope and state

- API prefix: `/api/v1/document-operations`.
- First supported kind: `pdf_split` only.
- Input lifecycle: `queued → processing → completed`, or `failed` /
  `unavailable` when an integrity or storage condition fails.
- Output is `completed` only after a fresh PDF has been written, size/hash
  checked and parsed again. The UI never turns a failed/guarded record into an
  output card or download.
- The Web route uses the same practical range behavior as the audited Bot:
  one page (`2`) or one contiguous range (`2-5`); a reversed range (`5-2`) is
  normalized. Comma-separated page lists are not accepted.

## Private input and output boundaries

1. The browser selects a current-account `.pdf` record from **Asset Vault**.
   It never uploads bytes, sends a local path, storage key, URL, Telegram file
   ID or provider handle to Document Operations.
2. The server owner-scopes the Asset Vault row, requires active state,
   canonical PDF MIME/extension, a maximum source of 20 MiB, and copies a
   SHA-256-verified source into an isolated operation staging area before
   parsing. A tampered source is marked unavailable rather than processed.
3. Generated output uses a root separate from Asset Vault and Project Package
   storage. It is never mounted under `/static`, included in the PWA shell,
   copied into a Bot asset table or exposed through a public URL.
4. The PDF parser is bounded to 30 source pages and rejects encrypted PDFs.
   A fresh writer copies only selected pages and omits annotations, automatic
   actions and other interactive page metadata before creating neutral output
   metadata.
5. The completed output is reparsed and hash/size checked. Download is a
   same-origin attachment endpoint with signed-session ownership checks,
   `no-store, private`, `nosniff`, `no-referrer` and `sandbox` response
   headers. A missing or tampered output becomes `unavailable`.

## Required configuration

Document Operations is disabled by default. It may be enabled only together
with Asset Vault on a persistent volume:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

In production each root must be an absolute child of the Web service's
Railway volume (`RAILWAY_VOLUME_MOUNT_PATH` or `/data`). The server rejects a
relative/static path, a volume root itself, or any overlap/nesting between
Document Operations, Asset Vault and Project Package roots. Enabling Document
Operations while Asset Vault is disabled is a startup configuration error.

`pypdf` is a Web-only parser dependency. It is imported only when Document
Operations is enabled; application startup fails closed if the enabled parser
runtime is absent.

## Request protections

- A signed account and CSRF token are required for creation; all reads and
  downloads are owner-scoped.
- Creation uses a server-validated idempotency key and request fingerprint
  based on the asset ID, normalized range, source hash and source size.
  Reusing a key for different intent returns conflict.
- A per-IP endpoint gate limits PDF Split creation before parsing. Source,
  page, output, account quota and storage checks remain server-side.
- Public envelopes redact storage keys, SHA-256 values, filesystem paths,
  parser traces, provider/payment data and source blob metadata.
- Startup reconciliation removes old unreferenced staging/output files and
  marks only stale interrupted `queued`/`processing` records as failed; it
  never exposes or moves referenced private artifacts.

## Explicit non-goals

- No browser-to-provider call, FFmpeg/PDF command shell, webhook, PayOS
  callback, wallet/credit mutation, manual top-up or Bot bridge call.
- No public preview, browser cache, PDF content extraction, OCR, merge,
  compression or translation. Those require separate reviewed capabilities.
- No claim that Bot's document routes are now Web jobs. This is an independent
  professional Web document utility with its own ownership and delivery
  contract.
