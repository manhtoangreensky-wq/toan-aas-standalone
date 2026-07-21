# Memory menu and callback disposition contract

The standalone Web Memory Center is a signed, Web-owned notes and reminders workspace. The frozen Bot's Memory menu, dynamic note identifiers, storage quota and storage add-on checkout are separate source concerns. A Browser never receives a raw callback token, Telegram identity, Bot note ID, pending text, search query, Bot record, quota, add-on, order or checkout state.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| menu\|main_memory | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_MEMORY_MENU_CONTEXT_NOT_REPLAYED, BOT_STORAGE_QUOTA_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|hint_note | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_PENDING_NOTE_INPUT_NOT_REPLAYED, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|hint_search_note | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_PENDING_SEARCH_QUERY_NOT_REPLAYED, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| freehub\|docs | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_FREEHUB_CONTEXT_NOT_REPLAYED, BOT_MEMORY_AND_STORAGE_STATE_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| freehub\|notes | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_FREEHUB_CONTEXT_NOT_REPLAYED, BOT_MEMORY_AND_STORAGE_STATE_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|hint_remind | /reminders | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_REMINDER_NAVIGATION, BOT_COMMAND_GUIDANCE_NOT_REPLAYED, TELEGRAM_REMINDER_DELIVERY_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| memory\|create | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_PENDING_NOTE_INPUT_NOT_REPLAYED, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| memory\|list | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| memory\|search | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_PENDING_SEARCH_QUERY_NOT_REPLAYED, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| memory\|delete_start | /notes | reviewed_memory_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_MEMORY_NAVIGATION, BOT_NOTE_DELETE_SELECTION_NOT_REPLAYED, BOT_MEMORY_RECORDS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|memory_storage_status | TELEGRAM_ONLY | bot_canonical_memory_storage_requires_adapter | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, BOT_CANONICAL_MEMORY_STORAGE_QUOTA, BOT_STORAGE_ADDON_ENTITLEMENTS, NO_WEB_STORAGE_STATUS_ADAPTER, NO_RUNTIME_CLAIM |
| menu\|memory_storage_addon | TELEGRAM_ONLY | bot_canonical_memory_storage_requires_adapter | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, CANONICAL_BOT_STORAGE_ADDON_CATALOG, CANONICAL_BOT_PAYOS_CHECKOUT, CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT, NO_RUNTIME_CLAIM |
| menu\|memory_storage_cleanup | MEMORY_STORAGE_CLEANUP_CONTRACT_REQUIRED | bot_storage_cleanup_guidance_requires_web_storage_contract | NEEDS_FEATURE_DISPOSITION | BOT_STORAGE_CLEANUP_GUIDANCE_ONLY, BOT_TEMP_FILE_TTL_NOT_REPLAYED, NO_WEB_STORAGE_CLEANUP_EQUIVALENCE, NO_RUNTIME_CLAIM |
| memory\|delete_yes\|{*} | TELEGRAM_ONLY | bot_memory_record_identifier_requires_telegram_context | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, BOT_MEMORY_NOTE_IDENTIFIER, BOT_MEMORY_RECORD_STATE, NO_RUNTIME_CLAIM |
| memory\|delete\|{*} | TELEGRAM_ONLY | bot_memory_record_identifier_requires_telegram_context | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, BOT_MEMORY_NOTE_IDENTIFIER, BOT_MEMORY_RECORD_STATE, NO_RUNTIME_CLAIM |
| memory\|view\|{*} | TELEGRAM_ONLY | bot_memory_record_identifier_requires_telegram_context | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, BOT_MEMORY_NOTE_IDENTIFIER, BOT_MEMORY_RECORD_STATE, NO_RUNTIME_CLAIM |
| other memory\|{*} | BOT_MEMORY_SOURCE_REVIEW_REQUIRED | memory_callback_template_requires_source_review | NEEDS_FEATURE_DISPOSITION | BOT_MEMORY_STATE_OR_IDENTIFIER_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

The reviewed navigation entries open a **fresh** signed Web form/list only. They do not inspect, copy or mutate Bot `memory_*` tables, and reminder navigation does not claim Telegram, email, push or any other delivery. `menu|memory_storage_status` and `menu|memory_storage_addon` remain Telegram-only until a separate owner-scoped canonical storage adapter is designed. `menu|memory_storage_cleanup` is intentionally not mapped to archive or Asset Vault retention: the Bot action only gives cleanup guidance and does not delete data.

A dynamic `memory|view|{*}`, `memory|delete|{*}` or `memory|delete_yes|{*}` value carries a Bot record identifier and remains Telegram-only. Any other dynamic `memory|{*}` value requires source review before it can gain a Web contract.
