# Memory Center & Reminders — Web-native contract

## Purpose and authority boundary

`/notes` and `/reminders` turn the useful personal organisation flow in the
frozen Telegram Bot baseline into a professional, signed Web workspace. The
data model is deliberately **Web-owned**: it is not a bridge, proxy, replica
or migration of Bot `memory_*` tables.

| Surface | Owner | It never does |
| --- | --- | --- |
| `/notes`, `/api/v1/memory/notes*` | Standalone Web App / signed Web account | Reads or writes Bot notes, calls a provider, creates a job, charge, Xu or payment |
| `/reminders`, `/api/v1/memory/reminders*` | Standalone Web App / signed Web account | Sends Telegram/email/push, starts a Bot worker, claims external delivery or mutates Bot reminder state |
| Bot `memory_notes`, `memory_reminders`, `memory_events` | Telegram Bot | Becomes visible to the Web route through a raw Telegram ID or browser token |

Every record is scoped to the authenticated Web account. UUIDs are only
identifiers; authorization never relies on their unguessability.

## Frozen Bot parity map

Static audit evidence is the frozen local Bot baseline
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`, including its note/reminder
tables and handlers around `bot.py:3531` and `bot.py:87055`–`87789`.

| Bot command / capability | Web-native equivalent | Boundary / status |
| --- | --- | --- |
| `/note`, `/notes`, `/note_view` | Create, list and owner-scoped detail on `/notes` | Implemented Web-owned notes with title, content, category, tags and priority. |
| `/search_note`, `/note_tags`, `/note_category`, `/notes_category`, `/notes_important`, `/note_priority` | Search/filter form plus `GET /api/v1/memory/notes` | Search includes title, content, tags and category; priority/state filters are explicit. |
| `/note_archive`, `/note_delete` | `POST /notes/{id}/archive`, restore | Matches the Bot's own soft-archive safety intent; no destructive browser delete. |
| Bot note history is absent | Immutable `web_memory_note_versions` | Web improvement: every content save and restore produces a new revision. |
| `/remind` | `POST /reminders` with `repeat_rule=none` | One-time schedule in declared `Asia/Ho_Chi_Minh` or `UTC`. |
| `/repeat_daily`, `/repeat_weekly`, `/repeat_monthly`, `/repeat_yearly` | `POST /reminders` with a repeat rule | Server advances calendar-aware next-run time only after explicit complete. |
| `/note_remind` | Optional `note_id` on a Web reminder | Only an active note owned by the same Web account can be linked. |
| `/reminders`, `/reminder_done`, `/reminder_cancel`, `/reminder_pause`, `/reminder_resume` | List and explicit lifecycle actions on `/reminders` | Implemented with optimistic revision, idempotency and audit. |
| Bot `process_due_memory_reminders` sender | Overdue/read state only | **Not copied**. The Web never claims a Telegram/email/push delivery without a future audited adapter. |
| `/note_ai` classification | Manual tagging/category/priority | **Guarded gap**. No provider or Xu/charge adapter is invoked, and the Web never fabricates an AI classification. |
| `/memory_status`, storage quota/add-on and PayOS storage checkout | None in this module | Remains Bot/canonical billing scope; the Web Memory Center does not duplicate quota, ledger or webhook logic. |

## Parent-menu navigation boundary

The following finite Bot entries can open a **fresh** Web workspace. This is a
navigation conversion, not a data migration: the browser receives neither a
raw callback, Telegram identity, Bot note/reminder row, pending text/query,
storage quota, add-on entitlement nor payment context.

| Bot entry | Fresh Web destination | What is deliberately not replayed |
| --- | --- | --- |
| `menu|main_memory`, `freehub|docs`, `freehub|notes` | `/notes` | Bot Memory/Free Hub context, Bot notes, reminder rows, storage quota and add-ons |
| `menu|hint_note`, `menu|hint_search_note`, `memory|create`, `memory|list`, `memory|search`, `memory|delete_start` | `/notes` | Bot pending note/search text, list, note ID, deletion selection or mutation |
| `menu|hint_remind` | `/reminders` | Bot reminder state and Telegram/email/push delivery state |

`menu|memory_storage_status` and `menu|memory_storage_addon` remain
`TELEGRAM_ONLY`: they respectively read Bot canonical quota/entitlements or
enter the Bot storage/PayOS checkout flow. `menu|memory_storage_cleanup` now
opens only the separate signed Web Workspace Care directory; it remains
guidance and does not map to archive or Asset Vault retention, inspect quota,
delete data or act on Bot storage. Dynamic
`memory|view|{*}`, `memory|delete|{*}` and `memory|delete_yes|{*}` remain
Telegram-only because their opaque identifier resolves a Bot-owned note, and
the confirmation can mutate that canonical record.

## State model

### Notes

```text
active ──archive──> archived
archived ──restore──> active
active ──update / restore-version──> active (revision + 1)
```

An archived note is retained and cannot be edited or restored to an old
version until it is restored. Linked reminders are intentionally untouched by
archiving: state changes must be customer-explicit.

### Reminders

```text
active ──pause──> paused ──resume──> active
active ──complete (one-time)──> completed
active ──complete (recurring)──> active with a next_run_at in the future
active|paused ──cancel──> cancelled
```

`completed` and `cancelled` are terminal. An overdue reminder is a Web UI
signal only, not evidence that a notification was sent. Local calendar month
and year changes clamp safely (for example, the 31st to the last valid day),
and recurrence has a bounded advance loop.

## API contract

All endpoints return the standard envelope and require the signed session.
All mutations additionally require CSRF, an account-scoped idempotency key
and server-side ownership/revision checks.

```text
GET  /api/v1/memory/summary
GET  /api/v1/memory/notes?limit=&state=&q=&priority=&category=
POST /api/v1/memory/notes
GET  /api/v1/memory/notes/{note_id}
POST /api/v1/memory/notes/{note_id}/update
POST /api/v1/memory/notes/{note_id}/archive
POST /api/v1/memory/notes/{note_id}/restore
POST /api/v1/memory/notes/{note_id}/restore-version/{revision}
GET  /api/v1/memory/reminders?limit=&state=
POST /api/v1/memory/reminders
POST /api/v1/memory/reminders/{reminder_id}/update
POST /api/v1/memory/reminders/{reminder_id}/complete
POST /api/v1/memory/reminders/{reminder_id}/pause
POST /api/v1/memory/reminders/{reminder_id}/resume
POST /api/v1/memory/reminders/{reminder_id}/cancel
GET  /api/v1/memory/events
```

The Portal calls only these same-origin Web endpoints. Search filter state is
kept in the mounted page state, not localStorage or the customer-visible page
URL. The owner-scoped API request carries the transient query parameters; they
are not persisted or handed to the Bot. The
service worker caches only public shell assets, never Memory APIs or content.

## Security and privacy controls

- The router imports no Bot bridge and makes no provider, wallet, PayOS,
  Telegram-send or job call.
- Read/write queries always include `account_id`; a missing or other-owner
  UUID returns a guarded response without leaking title/content.
- Notes/reminder bodies, tags and search input reject API keys, bearer tokens,
  passwords and card-like numbers. Audit entries contain only a bounded
  operation label and object UUID, never title, content, reminder body or
  query text.
- Notes are bounded to 1,000 active records per account; active/paused
  reminders are bounded to 250. Individual field lengths, tags, timezone and
  recurrence values are constrained server-side.
- `revision` prevents silent overwrites. Reusing an idempotency key with a
  different request fingerprint returns a conflict instead of performing a
  second write.
- Memory writes use the Portal's bounded write rate gate. The module is
  disabled fail-closed whenever `WEBAPP_MEMORY_CENTER_ENABLED=false`.

## Configuration and durability

```text
WEBAPP_MEMORY_CENTER_ENABLED=true
WEBAPP_SESSION_DB_PATH=<persistent-volume database path in production>
```

The capability defaults to `true` because it is a local Web workspace and has
no provider/payment dependency. Production data is durable only when the
Web-owned session database is placed on the configured Railway persistent
volume. This contract does not claim a live deployment, background scheduler
or notification delivery.

## Verification

Focused API and static Portal tests cover signed-session/CSRF protection,
owner isolation, idempotency collision detection, note versions, archive and
restore, reminder update/lifecycle/recurrence, expired-date rejection,
secret/audit redaction, flag fail-closed behavior, Portal search/filter,
bridge/payment separation and PWA non-caching. Full project regression is
required before merge; all provider, PayOS and Telegram flows remain mocked
or outside this module.
