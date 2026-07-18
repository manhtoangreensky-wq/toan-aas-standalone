# Admin Internal Document Archive — Web-native contract

Status: **opt-in Web-local-admin contract**. This is a private record archive
for signed Web administrators. It is deliberately separate from both the
customer Asset Vault and the text-only Governance Documents Center. Enabling
the feature is not a claim of a production migration, a legal-retention
decision, or a Bot integration.

## Bot mapping and explicit migration boundary

The frozen Bot is read-only reference material. Its useful interaction model
is mapped, while its state and Telegram transport remain **TELEGRAM_ONLY**:

| Bot reference | Web mapping | Boundary |
| --- | --- | --- |
| `/internal_docs`, `/search_internal_doc` | Private Admin Internal Document Archive page and metadata search | No Bot command execution or callback forwarding |
| `archive|dept|*`, `archive|type|*`, `archive|quick`, `archive|recent`, `archive|search*` callbacks | Server-validated department/type selection, upload, list and search | No Telegram conversation state or notification |
| `internal_documents` table, `owner_admin_id`, Telegram attachment/file identifiers | `web_admin_archive_documents`, `web_admin_archive_versions`, `web_admin_archive_events` | No read, write, copy, migration or reconciliation of Bot records/files |
| Bot recent/detail/send-file workflow | Owner-scoped list/detail and verified private Web download | No Telegram `send_document`, file ID, chat ID or public URL |

Historical Bot records remain in their original authority. The Web archive does
not infer ownership from Telegram identity and does not import old metadata or
attachments. A future one-time migration would require a separate signed,
audited export/import plan and is outside this release.

## Authority and enablement

The feature is available only if both server-side gates are deliberately true:

```text
WEBAPP_ADMIN_ERP_ENABLED=true
WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED=true
```

`WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED` defaults to `false`. Feature flags
only expose a route; they never grant a role. Every read requires a live
signed Web administrator session checked by the server. Every mutation also
requires CSRF, a live session re-check within its transaction, owner scoping,
an idempotency key, optimistic lifecycle revision and the relevant explicit
confirmation.

The browser never supplies an administrator ID, Telegram ID, role, storage
path, object key, SHA-256, content type authority, quota decision or a
canonical Bot permission assertion.

## Web surfaces

The private Admin routes are:

```text
/admin/internal-documents
/admin/internal-documents/documents/{uuid}

GET  /api/v1/admin/internal-documents/policy
GET  /api/v1/admin/internal-documents/summary
GET  /api/v1/admin/internal-documents/documents
POST /api/v1/admin/internal-documents/documents/upload
GET  /api/v1/admin/internal-documents/documents/{uuid}
PATCH /api/v1/admin/internal-documents/documents/{uuid}
POST /api/v1/admin/internal-documents/documents/{uuid}/versions/upload
GET  /api/v1/admin/internal-documents/documents/{uuid}/versions
GET  /api/v1/admin/internal-documents/documents/{uuid}/events
POST /api/v1/admin/internal-documents/documents/{uuid}/archive
POST /api/v1/admin/internal-documents/documents/{uuid}/restore
GET  /api/v1/admin/internal-documents/documents/{uuid}/download
GET  /api/v1/admin/internal-documents/versions/{uuid}/download
```

Responses use the standard Web envelope. Public projections omit object keys,
absolute paths, blob hashes, session IDs and other account IDs. A non-owner or
unknown record is handled as a guarded archive response rather than exposing
whether another administrator has a record.

## Isolated records, immutable versions and private storage

The archive owns three Web tables only:

- `web_admin_archive_documents` — owner-scoped metadata and lifecycle pointer;
- `web_admin_archive_versions` — immutable version metadata and integrity
  descriptor; and
- `web_admin_archive_events` — redacted lifecycle/version history.

Each accepted upload receives a server-generated private object key below a
dedicated archive root. A new file is a version; an existing version is never
overwritten. The normal lifecycle is `active → archived → active`; a missing,
changed, symlinked or hash-invalid blob becomes `unavailable` and fails closed.
There is no hard-delete, auto-purge, quota refund on archive, public share
link, browser-controlled path or file recovery by filename.

The first bounded release accepts only private PDF, DOCX and UTF-8 TXT files:

- at most 25 MiB per upload;
- at most 250 MiB retained across the local administrator's versions;
- at most 50 versions per document and 1,000 documents per local admin;
- PDF/DOCX structural checks, no encrypted PDF, unsafe ZIP path, macro/bin
  Office payload or malformed text; and
- secret-like content is rejected for text and all metadata fields.

Departments/types reuse the Bot's useful classification vocabulary, but they
are independent Web policy. Retention labels (`manual_review`, 3/5/10 years
or permanent) and confidentiality labels (`internal`, `confidential`,
`restricted`) are metadata only: they do not impose a legal hold, perform
automatic deletion, make a legal finding or create a notification.

## Upload, audit and delivery safeguards

Uploads are streamed into a private staging area, bounded before promotion,
then atomically moved under a generated object key after validation. The
server computes the digest, enforces document/account/version quotas and binds
idempotency to the validated metadata and bytes. A replay of the same request
returns the original receipt; reuse for materially different content is
rejected.

Metadata edits, version uploads, archive and restore use compare-and-set
`expected_revision`. Archive/restore require `confirm=true` and a fixed
acknowledgement phrase. Generic audit and archive events keep only an opaque
record ID, action, lifecycle/version numbers, state, safe byte/MIME facts and
request ID; they never store a title, filename, file content, raw tag,
storage key, hash, path, token or credential.

Before download, the server pins a non-symlink descriptor under the archive
root, verifies size and SHA-256, seals a rehashed temporary stream, and only
then emits an attachment. Responses are owner-scoped and include private
`no-store`, `nosniff`, `no-referrer` and sandbox protections. The PWA must not
cache archive APIs, downloads, page data or form state.

## Railway and deployment caveat

When enabled outside local/test, the archive must have a dedicated child of a
real persistent volume:

```text
RAILWAY_VOLUME_MOUNT_PATH=/data
WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT=/data/toanaas_webapp_admin_document_archive
```

The root cannot be relative, the volume root itself, within `static`, or shared
with Asset Vault, Project Packages, Document Operations or Image Operations.
Without an explicit root, local/test uses an isolated sibling of the session
database. The storage model assumes one persistent-volume replica; a
multi-replica deployment requires an object-storage adapter that preserves the
same descriptor, ownership, version and private-delivery guarantees.

Do not enable this flag in Railway merely because code is present. Provision
the volume, keep the root private, validate the focused test evidence and use a
separate rollout decision first.

## Explicit non-goals and external effects

This module does not import/call/change the Bot or Core Bridge; it does not
touch Telegram, provider APIs, Key4U, jobs, generated output delivery, Xu or
wallet ledger, PayOS, payment/webhooks, customer files, finance execution,
refunds, accounting, legal advice, external publish, email/SMS/web-push or
automatic repair/deploy. It is a Web-native local-admin archive only.

Focused verification must cover flag defaults, signed-admin/CSRF enforcement,
owner isolation, strict multipart fields, filename/MIME/container/path guards,
idempotency mismatch/replay, stale revision, immutable versions, archive and
restore, descriptor/hash tampering, audit redaction, private headers and
volume-root validation. It must use mocks/local fixtures only and never
exercise Telegram, provider, PayOS or production storage.
