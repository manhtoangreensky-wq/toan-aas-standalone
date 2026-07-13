# Web-native PDF to images contract

`/documents/pdf-to-images` is a bounded **Document Operations** capability
owned by the standalone Web App. It maps the useful result contract of Bot
`/pdf_to_images` into a professional browser workflow: one private PDF is
rendered at 2×, one-page input delivers a private PNG, and multi-page input
delivers a private ZIP containing deterministic `page_001.png`… entries.

It has **No Bot bridge** execution: no Bot job, no Core Bridge request, no provider call, browser-canvas
fallback, wallet/Xu event, PayOS order/webhook, public asset service, or a
claim that a source PDF can be rendered successfully. A rejected source leaves
no substitute image or fake download.

## Lifecycle and delivery

- Customer page: `/documents/pdf-to-images`.
- Hub: `/documents` and legacy `/documents/pdf` now route to Document Studio
  instead of a generic bridge form.
- API: `POST /api/v1/document-operations/pdf-to-images`.
- Kind: `pdf_to_images`.
- Input: exactly one active, owner-scoped Asset Vault file with `.pdf` and
  `application/pdf`, maximum 20 MiB.
- Output for one source page: `image/png`, named
  `toan-aas-pdf-page-001.png`.
- Output for two or more source pages: `application/zip`, named
  `toan-aas-pdf-pages.zip`, containing exactly `page_001.png` through the
  final source page. No directory, duplicate, traversal, unexpected, or
  externally supplied ZIP member name is allowed.
- States are `queued → processing → completed`; parser, integrity, renderer,
  pixel, archive and output failures are recorded as `failed` with no stored
  artifact. A stale/corrupt committed artifact becomes `unavailable` on its
  next owner-scoped download check.
- `source_page_count` and `output_page_count` are both server-verified. The
  browser never supplies page count, MIME, storage key, output name, URL,
  source bytes or path.

## Bot parity and intentional Web hardening

The audited Bot helper opens a PDF with PyMuPDF, renders every page using
`Matrix(2, 2)`, sends a single PNG for one page and a deflated ZIP for multiple
pages. Its useful bounds are 20 MiB and 30 pages.

The Web preserves that visible 2×/PNG-or-ZIP contract but uses
`pypdfium2==5.11.0` (PDFium) as its independently reviewed raster runtime.
This avoids adding a second Web dependency on the Bot's PyMuPDF runtime while
using the same output scale. The Web adds checks that the old direct Telegram
helper does not own:

- strict `pypdf` parse and encrypted-PDF rejection before PDFium rendering;
- owner-scoped Asset Vault read followed by a hash/byte/magic verified copy
  into isolated staging;
- maximum 30 pages, 8,192 pixels per rendered edge, 8 MP per page and 48 MP
  across a request before page bitmap allocation;
- one process-wide renderer slot, acquired only after signed owner and
  idempotency lookup; a second new request gets 429 without a lifecycle row;
- maximum 8 MiB per rendered PNG and 32 MiB aggregate PNG bytes before ZIP;
- a final artifact size cap from `WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB`
  (default 20 MiB, bounded 1–50 MiB);
- fresh Pillow validation of every renderer-produced RGB PNG, including magic,
  PNG parser verification, decoded geometry and pixel bounds;
- fresh ZIP verification for multi-page output: exact order/names, DEFLATE,
  member count/sizes, per-member PNG hash/geometry and no archive comment;
- atomic promotion followed by final full-file hash/size verification.

The feature uses no shell converter or external command. It is synchronous but
bounded; it does not manufacture a queued worker, background provider job or
completion state that does not exist.

## Authentication, ownership and replay protection

Writes require a signed Web session and CSRF. The `source_asset_id` is looked
up with the signed `account_id`; another Web account receives the same guarded
not-found response and cannot discover the source or operation. Every request
needs an idempotency key bound to the exact source asset ID, hash, byte size and
2× render version. Exact replays return the existing owner-scoped lifecycle;
the same key with a changed source receives 409.

The output endpoint also requires the signed owner. It resolves only a
server-owned suffix/MIME/name for the completed kind and verified page count,
then serves an attachment with `Cache-Control: no-store, private`, `nosniff`,
`no-referrer` and CSP sandbox headers. It never trusts mutable database
filename/MIME fields, exposes storage keys/hashes, or creates a public/static
URL. Service worker policy must continue to exclude this private route.

## Configuration

The feature is fail-closed unless all storage and renderer boundaries are
explicitly configured:

```text
WEBAPP_ASSET_VAULT_ENABLED=true
WEBAPP_ASSET_VAULT_ROOT=/data/toanaas_webapp_assets
WEBAPP_DOCUMENT_OPERATIONS_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_ROOT=/data/toanaas_webapp_document_operations
WEBAPP_PDF_TO_IMAGES_ENABLED=true
WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB=20
WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB=100
```

`WEBAPP_PDF_TO_IMAGES_ENABLED` defaults to `false`, independently of base
Document Operations. Startup loads PDFium only when this switch is true. The
route also uses the existing document-operation request rate gate. Production
must use the same persistent private volume policy as Asset Vault/Document
Operations; enabling the flag on ephemeral storage is intentionally rejected
by the persistence boundary.

## Required release evidence

Tests cover real one-page PNG and multi-page ZIP render results, expected 2×
geometry/names, CSRF/session, owner isolation, scoped history, idempotent
replay/conflict, renderer capacity, encrypted/31-page/tampered sources,
disabled gate, final artifact tampering, attachment headers/MIME and no
storage/provider/payment/Bot leakage. Static tests cover the native route,
flag, UI action, owner-scoped hydration and generic bridge rejection. Full
tests, syntax checks and `git diff --check` are required before opening a PR.
