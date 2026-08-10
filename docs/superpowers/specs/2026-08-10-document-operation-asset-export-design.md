# Document Operation Asset Vault Export Design

## Goal

Allow a signed Web account to save one completed, verified Document Operation
artifact into its private Asset Vault without downloading it into the browser
first. The export is a server-side copy with a fresh Asset Vault object and a
separate audit receipt; it never reuses a Bot file, public URL, provider job,
wallet balance, PayOS payment, or browser file path.

## Scope

The first release accepts only completed Document Operations with a stable,
unambiguous Asset Vault media contract:

| Document Operation kind | Exported extension | Media type |
| --- | --- | --- |
| `pdf_split`, `pdf_merge`, `pdf_optimize`, `image_to_pdf` | `.pdf` | `application/pdf` |
| `pdf_to_word_text`, `pdf_ocr_word` | `.docx` | Office Open XML document |
| `image_ocr`, `pdf_ocr` | `.txt` | UTF-8 `text/plain` |

`pdf_to_images` is deliberately excluded. Its output can be either a single
PNG or a ZIP, so it needs an explicit future artifact contract instead of a
generic export shortcut. Failed, guarded, queued, processing, unavailable, or
tampered outputs never create an Asset Vault row.

## Authority and safety boundary

Document Operations remains the canonical owner of its private operation
record, sealed output stream, output hash and artifact-specific parser checks.
Asset Vault remains the canonical owner of the new copied blob, lifecycle and
metadata. The browser supplies only the path operation UUID and an
idempotency key; it cannot submit source bytes, a filename, MIME type, hash,
storage key, URL, filesystem path, project ID or export policy.

The feature is Web-native only. It is not a mapping for a raw `docflow|*`
callback and does not call the Core Bridge, Bot, provider, wallet, payment,
refund, webhook or job API. It is off unless Asset Vault, Document Operations
and a dedicated `WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED` capability are all
effective. Adding the code flag does not change an environment value.

## Export protocol

1. `POST /api/v1/document-operations/{operation_id}/export-to-asset-vault`
   requires a signed account, CSRF and a validated `Idempotency-Key` header.
2. Document Operations validates the UUID, owner, `completed` state, exact
   export kind, stored server MIME/extension, byte size and SHA-256. It opens
   the output through its existing descriptor-pinned private reader and
   returns an opaque source object; no path or stream reaches the browser.
3. Asset Vault reserves a fenced lease in a document-specific relation table.
   The request map binds account, idempotency key, operation ID and source
   fingerprint. An existing completed relation returns its current Asset Vault
   receipt; a live lease returns `processing`; an expired lease may be safely
   reclaimed by a newer generation.
4. The current lease copies the pinned source into a private Vault staging
   object while recalculating byte count and SHA-256. Promotion must create a
   new random Vault object and must never replace an existing object.
5. Asset Vault reopens the promoted object through its private reader and
   independently verifies the exact allowed artifact:
   - PDF: strict parser, expected page count when present, no byte/hash drift.
   - DOCX: bounded OOXML archive with the required Word document entry.
   - TXT: strict UTF-8, non-empty bounded content and no byte/hash drift.
6. One fenced transaction inserts the Asset Vault metadata, records the
   completed relation and audit event. If the lease is stale, no Asset Vault
   success is returned and the pending object is removed. A copied asset keeps
   the operation's active Project only when it still belongs to the same
   account; otherwise it is unprojected.

## Public response

The route uses the standard envelope. A completed response exposes only safe
Asset Vault metadata (`id`, display name, extension, MIME, byte size, state
and timestamps). It never exposes a path, SHA-256, source text, document
contents, original operation storage key, provider details or a public URL.
The receipt is reread from current Asset Vault lifecycle state on replay, so
an archived or unavailable copied asset is never reported as an old success.

## Portal behavior

Every eligible completed Document Operation card shows one explicit “Lưu vào
Asset Vault” action and confirmation. The client uses the existing
CSRF-aware API helper plus a browser-generated idempotency key. It sends no
body and no document bytes. On success it refreshes the current Document
Operation history and Asset Vault projection; when guarded or pending it uses
truthful Vietnamese copy and does not invent a download or asset card.

The capability is distinct from normal Document Operation execution and has
its own narrow early POST rate limit. Service worker policy continues to
exclude all Document Operation and Asset Vault private requests and outputs.

## Persistence

Add non-destructive tables analogous to the already-reviewed image export
lease, but never share or mutate image export records:

- `web_document_operation_asset_exports`: one operation/account relation,
  immutable source fingerprint, fenced lease generation/token/expiry, pending
  storage key, reserved bytes, Asset Vault ID and lifecycle timestamps.
- `web_document_operation_asset_export_requests`: account-scoped
  idempotency-key mapping to one operation and fingerprint.

Both tables are created with `CREATE TABLE IF NOT EXISTS` and supporting
indexes only. No existing wallet, payment, Bot, job or user records are
migrated or rewritten.

## Acceptance checks

- A real verified PDF, DOCX and TXT output can each become one private,
  owner-scoped Asset Vault object.
- Cross-account access, changed idempotency binding, unsupported ZIP/PNG,
  incomplete operation, tampered source/output and stale lease all fail
  closed without creating an asset.
- Replays do not duplicate blobs, quota, audit success or Asset Vault rows.
- Browser code has no document bytes, URL/path or provider/payment surface.
- Existing document download, image export, Asset Vault upload/lifecycle and
  migration audit behavior remain unchanged.
