# Memory menu and callback disposition contract

The standalone Web Memory Center is a signed, Web-owned notes and reminders
workspace. The frozen Bot's Memory menu, dynamic note identifiers, storage
quota and storage add-on checkout are separate source concerns. A browser
never receives a raw callback token, Telegram identity, Bot note ID, pending
text, search query, Bot record, quota, add-on, order or checkout state.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| `menu|main_memory` | `/notes` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Memory navigation; Bot menu context and storage quota are not replayed |
| `menu|hint_note`, `memory|create` | `/notes` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Memory navigation; Bot pending note input and records are not replayed |
| `menu|hint_search_note`, `memory|search` | `/notes` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Memory navigation; Bot pending query and records are not replayed |
| `memory|list`, `memory|delete_start` | `/notes` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Memory navigation; Bot rows, note IDs and delete selection are not replayed |
| `freehub|docs`, `freehub|notes` | `/notes` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Memory navigation; Bot Free Hub, Memory and storage state are not replayed |
| `menu|hint_remind` | `/reminders` | `reviewed_memory_fresh_web_navigation` | `NAVIGATION_ONLY` | fresh signed Web Reminder navigation; Bot command guidance and Telegram delivery state are not replayed |
| `menu|memory_storage_status` | `TELEGRAM_ONLY` | `bot_canonical_memory_storage_requires_adapter` | `TELEGRAM_ONLY` | Telegram identity, canonical Bot quota and add-on entitlement; no Web storage-status adapter |
| `menu|memory_storage_addon` | `TELEGRAM_ONLY` | `bot_canonical_memory_storage_requires_adapter` | `TELEGRAM_ONLY` | canonical Bot storage catalog, PayOS checkout and entitlement settlement |
| `menu|memory_storage_cleanup` | `MEMORY_STORAGE_CLEANUP_CONTRACT_REQUIRED` | `bot_storage_cleanup_guidance_requires_web_storage_contract` | `NEEDS_FEATURE_DISPOSITION` | guidance only; Bot temporary-file TTL is not Web retention/cleanup parity |
| `memory|view|{*}`, `memory|delete|{*}`, `memory|delete_yes|{*}` | `TELEGRAM_ONLY` | `bot_memory_record_identifier_requires_telegram_context` | `TELEGRAM_ONLY` | Telegram identity, opaque Bot note ID/record state; `delete_yes` is a canonical Bot mutation |
| other `memory|{*}` | `BOT_MEMORY_SOURCE_REVIEW_REQUIRED` | `memory_callback_template_requires_source_review` | `NEEDS_FEATURE_DISPOSITION` | source-review-required Bot Memory state or identifier |

The reviewed navigation entries open a fresh signed Web form/list only. They
do not inspect, copy or mutate Bot `memory_*` tables, and reminder navigation
does not claim Telegram, email, push or other delivery. Storage status and
add-on purchase remain Telegram-only until an owner-scoped canonical storage
adapter is designed. Cleanup is intentionally not mapped to note archive or
Asset Vault retention because the Bot action only gives guidance and does not
delete data.
