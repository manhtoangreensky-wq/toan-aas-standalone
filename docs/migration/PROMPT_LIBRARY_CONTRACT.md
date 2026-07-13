# Prompt Library & Template Vault — Web-native contract

## Purpose and authority boundary

`/prompt-library` is a private authoring library for reusable prompt recipes.
It converts the useful **semantic** capabilities of the frozen Telegram Bot
Prompt Vault into a richer Web workflow: metadata, variable declarations,
immutable revisions, archive/restore, local preview and safe JSON transfer.
It does **not** import or expose the Bot's mutable global seed.

| Surface | Owner | It never does |
| --- | --- | --- |
| `/prompt-library`, `/api/v1/prompt-library/*` | Standalone Web App / signed Web account | Reads the Bot seed, sends Telegram, calls a provider, creates a job, writes Xu, PayOS or wallet state |
| Frozen Bot `TASK3D_PROMPT_VAULT` seed | Telegram Bot / staff workflow | Becomes customer-visible through a raw Telegram ID, browser storage or Web API |
| `web_prompt_*` tables | Standalone Web App | Stores a Bot identity, canonical payment data, provider request or generated output |

Every template is scoped by `account_id` on every read and mutation. A UUID is
only an identifier; authorization always comes from the signed server session.

## Frozen Bot parity map

The source reference is static-only, frozen at
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- Bot commands are registered around `bot.py:128948`–`128953`:
  `/prompt_vault_status`, `/prompt_vault_refresh`, `/prompt_vault_search`,
  `/prompt_vault_add`, `/prompt_vault_import` and `/prompt_vault_export`.
- Their handlers sit around `bot.py:104096`–`104143` and are staff/admin
  operations over the global seed.
- The Bot seed is `TASK3D_PROMPT_VAULT` around `bot.py:47364`; its model is
  `PromptVault` in `video_product_system.py:547`–`608`.

| Frozen Bot capability | Web-native equivalent | Boundary / implementation state |
| --- | --- | --- |
| `prompt_vault_status` | `GET /summary`, counts and local page summary | Implemented as a private account summary; it does not report Bot seed or staff diagnostics. |
| `prompt_vault_refresh` | Portal refresh plus owner-scoped `GET /templates` | Implemented; refresh only reads Web-owned SQLite data. |
| `prompt_vault_search` | Owner-scoped metadata/content search/filter | Implemented for title, prompt, negative prompt, category, context, platform, style, language and tags. |
| `prompt_vault_add` / import alias | Create form and bounded JSON import | Implemented with schema, DLP, CSRF, idempotency, quotas and audit. |
| `prompt_vault_export` | CSRF-protected `POST /export` browser Blob download | Implemented with an importable reduced schema; no storage object, URL fetch or shared link is created. |
| Bot `prompt_id` | Fresh opaque Web UUID | Intentionally not migrated; import never accepts a source ID. |
| `category`, `product_id`, `platform`, `style`, `language` | `category`, `product_context`, `platform`, `style`, `language` | Implemented as account-owned metadata. |
| `prompt_text`, `negative_prompt`, `variables` | Same semantic fields | Implemented as private text; declared variables power preview only. |
| `source`, `license_note`, `quality_score`, `enabled` | Same metadata plus `state=active|archived` | Implemented; `enabled` becomes an explicit archive lifecycle rather than a global staff toggle. |
| Bot `/video_prompt_vault_status` / multiscene diagnostic | None in customer Prompt Library | `TELEGRAM_ONLY` staff diagnostic. It is not a customer catalog or claimed engine readiness. |

The Web improves the Bot-only seed model by adding owner isolation, optimistic
revisions, immutable version records, audit events and an explicit provenance
field. It never overwrites Bot JSON or treats a Bot admin command as a Web
customer entitlement.

## State and version model

```text
active ──archive──> archived
archived ──restore──> active
archived ──purge (explicit confirmation)──> removed permanently
active ──update / restore-version──> active with revision + 1
```

An archived template is retained, cannot be edited, previewed or copied into a
new template until explicitly restored. Restore checks the active quota before
changing state. An archived template may instead be permanently purged only
after an explicit UI confirmation, CSRF, owner/revision check and audit event;
the template's private versions/events are removed with it. A normal state
change, update and restore-version creates an immutable snapshot. If an
**archive** operation reaches the strict history byte/revision ceiling, the
archive itself still completes with an audit/lifecycle event but intentionally
does not add a duplicate content snapshot; this lets the owner purge data and
recover capacity. Restore always requires capacity for its immutable snapshot.
One template retains at most 100 immutable revisions; a customer can
explicitly duplicate it to continue a new experiment rather than growing a
single SQLite history indefinitely.

The account keeps at most 1,000 active templates and 1,000 archived templates.
Those independent ceilings make archive/create cycles finite and prevent a
silent partial export of an older archive. A separate 24 MiB UTF-8 payload quota measures
both current template rows and immutable version rows, so the count ceilings
cannot turn the Web-owned SQLite database into an unbounded history store.

## API contract

All routes return the standard envelope except `POST /export`, which returns a
private JSON attachment after session and CSRF validation. Mutations require an
account-scoped idempotency key and server-side owner/revision checks.

```text
GET   /api/v1/prompt-library/summary
GET   /api/v1/prompt-library/templates?limit=&state=&q=&category=&platform=&product_context=&tag=
POST  /api/v1/prompt-library/templates
GET   /api/v1/prompt-library/templates/{template_id}
GET   /api/v1/prompt-library/templates/{template_id}/versions
PATCH /api/v1/prompt-library/templates/{template_id}
POST  /api/v1/prompt-library/templates/{template_id}/archive
POST  /api/v1/prompt-library/templates/{template_id}/restore
POST  /api/v1/prompt-library/templates/{template_id}/purge
POST  /api/v1/prompt-library/templates/{template_id}/duplicate
POST  /api/v1/prompt-library/templates/{template_id}/restore-version
POST  /api/v1/prompt-library/templates/{template_id}/preview
POST  /api/v1/prompt-library/import
POST  /api/v1/prompt-library/export
GET   /api/v1/prompt-library/events
```

`preview` substitutes only declared `{{variable}}` names in memory and returns
`execution: local_preview_only`. It never calls an AI engine, starts a job,
charges a customer or claims generated output.

### Import/export shape

The export file has the schema marker
`toan-aas-web-prompt-library-v1` and contains an array of these fields only:

```json
{
  "title": "...",
  "category": "...",
  "product_context": "...",
  "platform": "...",
  "style": "...",
  "language": "vi",
  "prompt_text": "...",
  "negative_prompt": "...",
  "variables": ["product"],
  "tags": ["launch"],
  "source": "...",
  "license_note": "...",
  "quality_score": 72,
  "state": "active"
}
```

It deliberately omits `account_id`, UUID, revision, timestamp and excerpt.
The Portal accepts either this wrapper's `templates` value or a direct array,
up to 50 items per import. The browser paste surface accepts at most 1,400,000
characters per batch; the server independently caps raw import bodies at 6 MiB
and rejects an overage before JSON parsing. It never accepts a file path, URL,
scraper input, global Bot seed or authority field.

## Security and privacy controls

- The router imports no Core Bridge and makes no Telegram, provider, wallet,
  PayOS, payment or job call.
- Every SQL lookup includes the signed `account_id`; cross-account or missing
  UUIDs receive a generic guarded response without leaking a title, tag,
  prompt or version count.
- Input rejects secret/token/password/bearer patterns, quoted secret
  assignments, PEM/OpenSSH private-key material, unsafe control characters,
  OTP/CVV, card-shaped strings and manual payment evidence.
- Mutation audit events contain an operation label, UUID/revision and request
  ID only. Prompt text, excerpts, source, license note and preview values are
  not written to audit detail or idempotency rows.
- Optimistic `expected_revision` prevents a silent overwrite. Reusing an
  idempotency key with a different redacted fingerprint returns a conflict.
- Successful mutation receipts are scoped to the Web account, retained for 24
  hours and capped at 2,048 per account. Guarded/no-op outcomes are not stored
  as receipts, so random failed keys cannot bloat the database.
- Export is a same-origin `POST` with CSRF rather than a forced cross-site GET.
  It is a no-store attachment with `nosniff`, `no-referrer` and `sandbox`
  headers. The Portal uses an in-memory Blob URL then revokes it; no export is
  written to server storage. It serializes rows incrementally and stops with a
  guarded JSON 413 response before an encoded export exceeds 24 MiB.
- All normal Prompt Library writes are capped at 512 KiB raw body size; import
  has the separately documented 6 MiB cap. The ASGI boundary checks both
  declared `Content-Length` and each chunk of a streamed body before
  FastAPI/Pydantic parsing, returning `WEB_PROMPT_LIBRARY_BODY_TOO_LARGE`.
  Explicitly allowed credentialed CORS origins receive the same safe envelope
  and headers on a 413 response.
- Read routes use a fixed family rate gate (120 requests/IP/minute) before the
  vault query; owner/session checks remain mandatory and are never inferred
  from a browser identifier.
- The service worker caches public shell files only. It never caches Prompt
  Library listings, details, previews, imports, exports or events.

## Configuration and durability

```text
WEBAPP_PROMPT_LIBRARY_ENABLED=true
WEBAPP_SESSION_DB_PATH=<persistent-volume database path in production>
```

The feature defaults to enabled because it is a local Web authoring surface,
not a provider/payment integration. It fails closed when the flag is off.
Production durability still requires that the Web-owned database uses the
configured persistent Railway volume. This contract makes no claim of a live
deployment, provider smoke test, Telegram operation or payment transaction.

## Verification

Focused backend and Portal contract tests cover session/CSRF protection,
owner isolation, idempotency replay/collision/expiry, DLP including quoted
secrets and private-key markers, version/archive/restore quotas, storage and
export byte ceilings, declared/chunked body caps, credentialed-CORS 413
headers, private round-trip export/import, local-only preview, route/client
wiring, responsive UI and PWA non-caching. Full regression and static Bot
migration audit remain required before merge. Provider, PayOS and Telegram
flows stay mocked or outside this module.
