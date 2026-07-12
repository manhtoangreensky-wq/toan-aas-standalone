# Web-native PDF Merge contract

`/documents/merge` is a bounded **Document Operations** capability owned by
the standalone Web App. It preserves the useful ordered-merge behavior in the
frozen Bot helper while deliberately providing stronger Web controls. The
Bot's direct merge command remains planned; this Web capability is not a Bot
job and does not create, read or alter Telegram identity, Xu, PayOS,
provider state or Bot asset delivery.

## Scope and lifecycle

- API: `POST /api/v1/document-operations/pdf-merge`.
- Kind: `pdf_merge`.
- Input lifecycle: `queued → processing → completed`, or `failed` /
  `unavailable` when an integrity or storage condition fails.
- The Web form exposes ordered slots **PDF 1 → PDF 8**. That order is part of
  the request fingerprint and is exactly the order in the generated PDF.
- A response becomes `completed` only after a new artifact is written,
  reparsed, size/hash checked and atomically promoted into private storage.
  The UI never renders an unverified result or a fake successful output.

## Input and output boundary

1. The browser submits two to eight distinct IDs for active `.pdf` files in
   the signed account's **Asset Vault**. It never submits bytes, local paths,
   storage keys, URLs, Telegram file IDs or provider handles.
2. Every source is owner-scoped, checked for canonical PDF MIME/extension,
   bounded to 20 MiB, SHA-256 verified while copied to isolated staging and
   opened with the strict PDF parser. Aggregate input is bounded to 40 MiB.
3. The aggregate document has at most 30 pages. Encrypted, empty, malformed
   and duplicate inputs are rejected. The write starts with a fresh writer
   and omits annotations, automatic actions and related interactive page
   metadata from every copied page.
4. The generated PDF has neutral metadata, a server-generated name, an
   output-size/account-quota check, strict reparse and SHA-256 verification
   before it is published. Output storage is separate from Asset Vault,
   Project Packages and `/static`.
5. Download is an owner-scoped, signed-session attachment endpoint. It uses
   `no-store, private`, `nosniff`, `no-referrer` and `sandbox`; PWA shell
   caching never includes document-operation API responses or files. A
   missing/tampered output becomes `unavailable` rather than downloading.

The operation row retains the first source only for compatibility. Its
immutable `web_document_operation_sources` map is authoritative for the
complete source set and source order; it stores server-verified input hashes
and sizes but those details never appear in browser responses or audit text.

## Configuration and request protection

PDF Merge uses the same deliberately opt-in persistent storage configuration
as PDF Split:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

All roots must be distinct absolute children of the Web service persistent
volume in production. The parser dependency is `pypdf`; enabled Document
Operations fail closed during startup if it is unavailable.

- Creation requires signed session, CSRF and a 12–160 character validated
  idempotency key.
- The server binds an idempotency key to the **ordered** source sequence,
  including each source ID, hash and byte size. Retry with identical intent
  returns the same operation; changing order or source under the same key is
  a conflict.
- A per-IP create gate applies before parsing. Limits on source count,
  source/aggregate bytes, pages, output size, account quota and storage stay
  server-side.
- Audit records contain only operation ID, source count, page count, byte
  count and outcome; no paths, filenames, hashes, asset IDs, PDF contents,
  provider, payment or wallet fields are recorded.
- Reconciliation removes unreferenced stale staging/output files and marks
  interrupted work failed. It cannot make an unverified artifact downloadable.

## Explicit non-goals

- No Bot bridge, browser-to-provider request, command shell/FFmpeg path,
  webhook, PayOS callback, manual top-up or Xu/ledger mutation.
- No browser PDF preview, OCR, compression, translation, merge of arbitrary
  URL/local files, or implicit conversion of a Web artifact into a Bot asset.
- No claim that a planned Bot command has become live. This is a separately
  secured Web-native utility with its own ownership, storage and delivery
  contract.
