# Document Operation → Asset Vault export contract

## Purpose and scope

This contract lets a signed Web account explicitly retain **one already
verified, completed Web-native Document Operation** as a separate private
Asset Vault record. It is a copy boundary, not a new document processor.

The feature is fail-closed. It is effective only when all three flags are
enabled on the Web service:

- `WEBAPP_ASSET_VAULT_ENABLED`;
- `WEBAPP_DOCUMENT_OPERATIONS_ENABLED`;
- `WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED`.

The public bootstrap publishes only the effective conjunction as
`document_operation_export_enabled`; the browser capability additionally
requires a signed account and CSRF token.

## Supported completed outputs

The server, not the browser, owns the fixed kind-to-artifact map.

| Document Operation kind | Retained Asset Vault artifact |
| --- | --- |
| `pdf_split`, `pdf_merge`, `pdf_optimize`, `image_to_pdf` | PDF (`.pdf`, `application/pdf`) |
| `pdf_to_word_text`, `pdf_ocr_word` | DOCX (`.docx`, OOXML Word MIME type) |
| `image_ocr`, `pdf_ocr` | UTF-8 TXT (`.txt`, `text/plain; charset=utf-8`) |
| `pdf_to_images` with `source_page_count == output_page_count == 1` | PNG (`.png`, `image/png`, `toan-aas-pdf-page-001.png`) |

`pdf_to_images` has one intentionally narrow per-file rule: only its sealed,
completed one-page PNG may be retained. A multi-page result remains a ZIP and
is always ineligible. This flow does not accept a ZIP, unpack an archive, pick
an individual page or let the browser select a filename, MIME type, page count
or Asset Vault destination.

## Request and response boundary

The only write endpoint is:

```text
POST /api/v1/document-operations/{operation_id}/export-to-asset-vault
```

It requires the signed account, CSRF protection and a valid opaque
`Idempotency-Key`. The browser submits only the canonical operation UUID and
the idempotency header. It never sends bytes, paths, names, MIME types, hashes,
source asset IDs, provider payloads or a chosen Vault destination.

Responses remain truthful:

- `completed` returns a current redacted private Asset Vault receipt;
- `processing` means a live copy lease still owns the operation and no new
  asset is claimed yet;
- `guarded` means eligibility, ownership, integrity or delivery verification
  failed and no replacement artifact is created.

The portal shows the quiet confirmed export action only for a completed,
download-ready supported output with the effective capability. Every document
workspace passes its active route context to the shared card renderer. The
client handler verifies that route before making one same-origin POST, then
rehydrates the operation history and Asset Vault from server state.

## Server-side copy lifecycle

1. The document router validates account ownership, completed state, allowed
   kind and the sealed output descriptor before reserving work.
2. Reservation records an owner-scoped request fingerprint and a fenced,
   expiring copy lease. The same idempotency key cannot be rebound to another
   operation or source fingerprint.
3. The finalizer copies the pinned stream into a private Vault staging path,
   rehashes it and validates the destination against the server-selected
   format contract.
4. It repeats the operation, lease, quota, ownership, provenance and project
   checks inside the transaction that creates the independent Asset Vault row.
5. A completed relation clears its transient lease fields and points to one
   private Vault record. Replay reads the **current** asset lifecycle instead
   of returning a stale success snapshot.

Current format verification is deliberately strict:

- PDF requires a valid parse, pinned size/hash and a terminal `%%EOF` with
  only valid trailing PDF whitespace.
- DOCX uses the bounded OOXML validator: safe archive structure and CRC,
  required Word parts, no traversal/duplicates/encryption/symlinks, macros,
  embeddings, ActiveX or external relationships.
- TXT must be bounded strict UTF-8, contain non-whitespace text and contain no
  NUL character.
- A retained PDF-to-images artifact must be one static RGB PNG with the exact
  one-page descriptor, PNG magic, full parser/decode, no eXIf chunk, one frame,
  no animation, at most 8 MiB, 8,192 pixels per edge and 8 MP total. The copied
  Vault file is reopened and rechecked for byte count and SHA-256 before its
  metadata row is committed.

Parser/runtime failures are treated as retryable destination failure and do
not silently demote the original completed document artifact.

## Persistence, quota and recovery

The Web-owned schema adds only these relations:

- `web_document_operation_asset_exports` for the fenced copy lifecycle;
- `web_document_operation_asset_export_requests` for account-scoped
  idempotency mapping.

These records have no provider, Bot, wallet, payment, PayOS or public-delivery
fields. Pending document-export bytes count with pending image-export bytes
against the same per-account Asset Vault quota. Expired leases may be reclaimed
only with a new fence token and generation; a stale finalizer cannot overwrite
the newer lease. Reconciliation removes only orphaned pending storage that is
not owned by a live lease.

## Privacy and non-goals

- Downloads remain signed-session, owner-scoped Asset Vault downloads; there
  is no public URL, browser Blob cache, PWA cache or raw storage key in the
  public response.
- A multi-page PDF-to-images ZIP remains private only to its Document
  Operation download; it cannot be uploaded, unpacked or retained by this
  Asset Vault export path.
- The feature does not modify `bot.py`, Core Bridge, Telegram identity,
  providers, Key4U, jobs, wallet/Xu, pricing, PayOS, webhooks or admin write
  authority.
- It does not create document output, invoke OCR/Word/PDF renderers, change
  the original operation, add a second webhook or claim provider success.

## Focused acceptance evidence

- Route, CSRF, owner scope, idempotency, ineligible/tampered source and
  current receipt lifecycle are covered by
  `tests/test_document_operation_asset_export.py`.
- Lease fences, shared quota, stale recovery and replay integrity are covered
  by `tests/test_document_operation_asset_export_leases.py`.
- PDF/DOCX/TXT finalization and source-failure domains are covered by the
  focused `test_document_operation_asset_export_*` suites.
- Portal capability/action, no-PWA-private-cache and active-context rendering
  are covered by `tests/test_document_operation_asset_export_portal_contracts.py`.
