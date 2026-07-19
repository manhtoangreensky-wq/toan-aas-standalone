# Free Prompt Gallery — static Web contract

## Purpose and Bot reference

The frozen Telegram Bot's Free Tools Hub contains a global prompt-seed library:

- `free_tools_hub.py`: `load_prompt_library`, `expand_prompt_library`, filtering and item lookup helpers;
- `data/prompt_library/free_hub_prompts.json`: 20 reviewed industries and 7 prompt categories (140 initial combinations).

`copyfast_free_prompt_gallery.py` is a standalone Web-native, **read-only snapshot** of that structure.  It does not import the Bot, open that JSON file, derive a path to the Bot, or share Bot runtime state.  The copied content is a reviewed product seed, not a live synchronization protocol.

## Mounting boundary

The production `app.py` mounts the router at `/api/v1/free-prompt-gallery` and the Portal exposes it at `/free-prompt-gallery`.  The gallery remains a separate, read-only product surface: it is not the Prompt Library vault, a Bot callback/runtime, or a global-write API.  The engine registry marks it Web-native only under the existing Content Studio availability gate.

Every endpoint requires the existing signed Web session (`require_account`).  They are read-only `GET` endpoints and therefore do not require CSRF; responses set `Cache-Control: private, no-store`, `Pragma: no-cache` and `Vary: Cookie`.

## Reviewed Free Hub library navigation boundary

The literal Bot callback `freehub|library` opens the same signed Gallery
surface. The only reviewed dynamic family is `freehub|lib_{*}`: the Bot uses
its finite suffixes (`video`, `image`, `meta`, `caption`, `shop`, `beauty`,
`random`) to choose a global prompt-library suggestion set and then stores a
short-lived Telegram pending selection.

The migration audit records `freehub|lib_{*}` as `NAVIGATION_ONLY` to
`/free-prompt-gallery`. It intentionally opens a fresh Gallery rather than
passing a suffix, suggestion list, ordinal, Bot prompt ID, Telegram user ID or
pending state into the browser. The Gallery can use only its own validated
catalog filters and stable Web item IDs. This is not a claim that Bot
suggestions, `lib_more`, `lib_back`, `lib_pick1..3`, a provider, job, wallet,
PayOS action or media output has been replayed on the Web.

## Explicit save into the private Prompt Library

The Gallery router itself remains read-only. A signed user can explicitly
save one reviewed seed through the private Prompt Library handoff:

| Endpoint | Contract |
| --- | --- |
| `POST /api/v1/prompt-library/gallery-items/{prompt_id}/save` | Resolves the item only from the immutable in-process Web snapshot and creates one owner-scoped Prompt Library template. The body accepts only `idempotency_key`. |

This handoff requires both the signed session and `X-CSRF-Token`, plus the
existing `WEBAPP_PROMPT_LIBRARY_ENABLED` flag. It does not accept prompt
text, title, tags, account ID, source, Bot ID or any provider/payment input
from the browser. The server validates the Gallery identifier, reuses the
normal Prompt Library content/secret guards, writes revision `1`, and records
an audit event `web.prompt_library.gallery_save` only when it creates a new
template.

`web_prompt_gallery_saves` is an owner-scoped provenance map keyed by
`(account_id, gallery_prompt_id)`. It makes repeated save clicks idempotent
even with a fresh retry key and retains the same owner template if that
template is later edited or archived. The map has an `ON DELETE CASCADE`
foreign key, so an explicit permanent Prompt Library purge removes the map
and permits an intentional future re-save. This is Web-owned provenance, not
a Bot pending-save, Telegram conversation, global seed library, or sync
protocol.

This narrowly covers only a selected static Gallery item. It does **not**
close the generic Bot `freehub|save` parity gap, because that callback may
refer to arbitrary pending Telegram conversation output rather than a known
Web Gallery ID. The migration audit therefore correctly keeps that broader
callback as `NEEDS_WEB_IMPLEMENTATION` until a separate, owner-safe Web
draft contract exists.

Successful handoff envelopes mark `template_persisted: true` and explicitly
retain `pending_bot_save_created`, `telegram_state_changed`, `bot_called`,
`bridge_called`, `provider_called`, `job_created`, `wallet_mutated`,
`payment_started`, `asset_saved`, `publish_action_created` and
`delivery_created` as `false`.

## Explicit save into the private Memory Center

The original Bot's `freehub|save` action records the selected pending result
as a note; it does not start an AI run, job, provider call, Xu mutation or
payment.  For the narrow case where the selected result is a known static Web
Gallery item, the Web App preserves that useful behavior through the Memory
Center:

| Endpoint | Contract |
| --- | --- |
| `POST /api/v1/memory/gallery-items/{prompt_id}/save` | Resolves one immutable Gallery item by ID on the server and creates an owner-scoped Web Memory note. The body accepts only `idempotency_key`. |

This mutation requires a signed session, `X-CSRF-Token`, and
`WEBAPP_MEMORY_CENTER_ENABLED`. The browser cannot submit prompt text, title,
tags, category, account ID, Bot ID, source metadata, provider settings or
payment information. The server resolves the static item through
`free_prompt_item`, writes one `web_memory_notes` row, revision `1` in
`web_memory_note_versions`, a normal `note_created` Memory event, a
sanitized `web.memory.gallery_item.save` audit event, and its idempotency
receipt in one transaction.

The successful save receipt deliberately returns the smallest useful metadata
only (`id`, category, priority, state and revision). It never echoes the raw
prompt and neither does the audit event; the complete reviewed seed is only
visible through the normal owner-scoped Memory note detail route. A retry
with the same idempotency key and selected item returns the same durable
receipt. Reusing that key for another item is rejected, so a browser retry
cannot silently save the wrong seed.

The response marks `memory_note_persisted: true` while keeping
`gallery_state_persisted`, `pending_bot_save_created`,
`telegram_state_changed`, `bot_called`, `bridge_called`, `provider_called`,
`job_created`, `wallet_mutated`, `payment_started`, `asset_saved`,
`publish_action_created` and `delivery_created` as `false`.

This is not a bridge to the Bot's temporary Telegram conversation state and
does **not** close the generic `freehub|save` parity gap. That callback can
refer to arbitrary pending Telegram output, which has no safe equivalent in a
static Gallery URL. The migration audit must continue to list the broader
callback as `NEEDS_WEB_IMPLEMENTATION` until each Web workflow supplies its
own owner-safe draft-to-Memory handoff.

## Endpoints

| Endpoint | Contract |
| --- | --- |
| `GET /catalog` | Ordered categories/industries, counts and fixed execution boundaries. |
| `GET /items` | Deterministic category-major/industry-minor list with strict `category_id`, `industry_id`, `goal`, `platform`, `q`, `page`, `page_size` filters. |
| `GET /items/{prompt_id}` | A single immutable snapshot item; malformed IDs return `422`, absent well-formed IDs return a `404` guarded envelope. |

Valid identifiers are the catalog IDs only.  Searches are whitespace-normalized, bounded to 160 characters and reject control characters plus credentials/secrets so a query cannot become an echo channel.  Page size is 1–50 and pages are 1–10,000.

The canonical expansion order is category first then industry, with one template in every category/industry pair.  This produces exactly 140 items and stable IDs such as `caption_cta_food_cafe_1`.  Filter and pagination helpers are pure functions so a later UI can use exactly the same deterministic behavior.

## Response and safety boundary

All successful responses use the standard envelope and include:

```json
{
  "execution": "web_native_static_prompt_gallery",
  "snapshot_read_only": true,
  "gallery_request_persisted": false,
  "provider_called": false,
  "bot_called": false,
  "bridge_called": false,
  "job_created": false,
  "wallet_mutated": false,
  "payment_started": false,
  "asset_saved": false,
  "publish_action_created": false,
  "delivery_created": false
}
```

The signed-session middleware may update its own last-seen timestamp; the gallery itself performs no persistence and owns no database table.  It does not create content, make AI/provider calls, call the core bridge, start payments, mutate Xu/wallet data, schedule or publish social content, create assets/jobs, or deliver media.  Prompt text is an editable seed only; users must verify facts, rights and claims before any external use.

## Verification scope

`tests/test_copyfast_free_prompt_gallery.py` mounts the module only in a temporary FastAPI test app with the real signed-session auth router.  It verifies signed-session access, no-store headers, all 20/7/140 catalog records, deterministic filter/paging/detail results, strict invalid/secret-filter rejection, boundary values and absence of Bot/database/bridge/provider/file-loading dependencies in the module source.
