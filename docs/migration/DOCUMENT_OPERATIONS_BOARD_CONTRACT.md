# Document Operations Board — canonical Web-native contract

## Purpose

`/documents` is the canonical **Document Operations Board** for a signed Web
account. This change upgrades the existing Document Studio route; it does not
create a second document hub, route family, database table, API namespace or
execution engine. The legacy navigation alias `/documents/pdf` keeps the same
board and the frozen `/doc_tools -> /documents` mapping remains unchanged.

The board helps a customer choose a bounded document workflow and inspect only
their recent verified operations. Individual workflow pages continue to own
their source selection, confirmation, output state and download UX.

| Surface | Existing authority | This board never adds |
| --- | --- | --- |
| `/documents`, `/documents/pdf` | signed portal renderer and existing document-operation history read | a document board table, browser store, new API, generic upload or new feature flag |
| `GET /api/v1/document-operations?limit=50&offset=…` | existing owner-scoped, redacted list of all supported document kinds when `kind` is omitted | cross-account data, raw path/hash/storage key, source bytes, preview URL or generated output |
| `/documents/*` workflow pages | existing Document Operations / Asset Vault contracts | Bot job replay, provider invocation, wallet/Xu/PayOS mutation or webhook |
| `/document-workspace` | independent signed Web authoring workspace | source preselection, draft transfer, shared lifecycle or automatic operation |

## Board read model and route behavior

The board reads the existing `/api/v1/document-operations` endpoint without a
`kind` query parameter. The server maintains account ownership, kind
allow-listing, pagination, public-envelope redaction and private download
checks. The browser accepts only the existing opaque operation metadata and
renders it through `renderDocumentOperationCards`.

The board therefore has these truthful states:

1. **Guarded** — the signed session, Asset Vault or Document Operations gate
   is unavailable. No previous account's history, Asset Vault list, Bot job or
   browser substitute is shown.
2. **Loading** — the existing signed, owner-scoped projection is in flight;
   the page has a stable processing state instead of a blank/fake list.
3. **Ready** — current-page metadata is rendered. A download link appears only
   for an existing `completed` operation with `download_ready=true`; the
   server repeats ownership and integrity checks on download.
4. **Failed** — the client clears operation/list pagination state and offers a
   signed refresh. It does not retry by inventing an artifact or source.

The explicit “Asset Vault” and “Document Workspace” links are fresh
navigations only. They carry no asset ID, filename, query, fragment, hidden
form state, browser-storage record or background request. Neither link can
preselect a file or run a document operation.

## Workflow boundaries

The board groups the existing tools only for discoverability:

- PDF basics: Split, Merge and Optimize;
- conversion: PDF to Images, Image to PDF and text-PDF to Word;
- OCR & scan: Image OCR, PDF OCR and PDF OCR to Word.

Each card stays linked to its own established route. A guarded card remains
navigable to its safe explanation and labels itself “Xem điều kiện”; it never
claims a ready runtime or offers a fake result. The board does not combine
Document Workspace authoring with PDF/OCR execution, and it does not broaden
the Bot's `docflow|*` callback disposition. Telegram-only callbacks remain
Telegram-only.

## Security, privacy and PWA

- The browser begins a read only after the existing signed-session capability
  gate. API ownership is canonical on the server; an opaque ID is not an
  authority token.
- The existing `document-operation-refresh` and pagination actions verify the
  current document route and signed capability before requesting the already
  available list. The board does not add write action names.
- `/documents` is explicit in the service-worker private-path policy. The
  full route family, including the combined history, bypasses Cache Storage
  and public offline navigation fallback after sign-out or account switching.
- No source PDF/image bytes, local path, storage key, source hash, private OCR
  text, provider payload, Blob/object URL or public file URL is inserted into
  the board. The server's current public projection remains the only data
  source.

## Non-goals

This presentation upgrade does **not** modify Bot code, Core Bridge,
providers, Key4U, jobs, wallet/Xu ledger, PayOS, payment webhook, admin write
authority, document-operation storage, download implementation, database
migration, runtime flag or execution pipeline. It neither adds a provider
fallback nor treats a Bot document callback as a Web job.

## Focused acceptance checks

- `/documents` and `/documents/pdf` use the existing unfiltered owner-scoped
  list, preserve pagination and clear stale state on failed reads.
- Every output card stays metadata-only; it has no source handoff, browser
  persistence, preview or fake download.
- PDF/OCR workflow pages, Asset Vault and Document Workspace remain separate
  and retain their existing server-side confirmation, ownership and delivery
  contracts.
- The board uses the app-first dark slate/teal system, grouped workflow
  headings, readable status text, visible keyboard focus, reduced-motion
  behavior and 44px mobile controls.
