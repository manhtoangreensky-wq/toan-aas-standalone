# State and database authority map

The bot remains the canonical writer for identity, wallet, PayOS, jobs, and provider state. The Web App consumes typed bridge contracts and must not duplicate those writes.

| Table set | Count | Examples |
| --- | --- | --- |
| Bot discovered | 554 | _update, _utils, _valid_url, a, above, acodec, active, affiliate_links, again, all, an, ang, ann, annot, any, api_debug_events, application, applies, are, arr, associated, attached, attributes, audit_logs, available, b2b_projects, belongs, birthday, birthday_gifts, birthday_review_requests |
| Web discovered | 224 | a, above, affiliate_links, any, b2b_projects, campaigns, clears, credit_events, erp_approvals, erp_assets, erp_attendance, erp_banners, erp_chat, erp_customers, erp_employees, erp_goals, erp_inventory, erp_okrs, erp_production, erp_projects, erp_purchases, erp_sales, erp_social, erp_transactions, erp_workloads, family, feedback, manual_orders, manual_performance_events, media_assets |
| Bot-only (bridge/read contract required) | 330 | _update, _utils, _valid_url, acodec, active, again, all, an, ang, ann, annot, api_debug_events, application, applies, are, arr, associated, attached, attributes, audit_logs, available, belongs, birthday, birthday_gifts, birthday_review_requests, bits_per_code, bot, broadcast_lite_auto_notices, broadcast_lite_blocked_users, broadcast_lite_campaigns |

## Bot Workboard and Task callback boundary

The Bot `pipe|*` and `task|*` callbacks are Telegram-admin transitions over canonical production job/task rows. A Web Workboard must use independently authorized Web work records or a separately reviewed redacted bridge/read model; it never accepts a Bot callback, job/task identifier, stage/status or handoff value. See `WORKBOARD_TASK_CALLBACK_CONTRACT.md`.


## Bot Creative variant callback boundary

The Bot `creative|*` callback is a Telegram-admin selection transition over canonical creative-variant and production-job rows. A Web Creative Studio must use independently authorized Web records or a separately reviewed redacted bridge/read model; it never accepts a Bot callback, variant identifier, selected state, production update or handoff value. See `CREATIVE_VARIANT_CALLBACK_CONTRACT.md`.


## Bot Audio Hub callback boundary

The Bot `music_quick|*`, `sfx_quick|*`, `media_quick|*` and `suggest_music|*` callback families are completely classified `TELEGRAM_ONLY`: they are Telegram state transitions or guidance over product context, guided pending input, music/SFX/media caches, selected media, voice-profile, Video Finishing state or Bot keywords. A Web Audio Hub must start from Web-owned owner-scoped data and never accepts/replays a Bot callback, cache index, profile ID, finalization value or keyword. This completed classification does not add a Web feature or runtime-equivalence claim; fresh Web-native alternatives remain non-executable with respect to raw Bot callbacks. See `AUDIO_HUB_CALLBACK_CONTRACT.md`.


## Additive Web-native Video Poster state

| Table | Owner | Purpose | Explicitly not authoritative for |
| --- | --- | --- | --- |
| `web_video_operations` | Signed Web account | One bounded private poster request, sealed output metadata and exact lifecycle | Bot jobs, provider execution, wallet/Xu, PayOS, Telegram identity or Asset Vault source ownership |
| `web_video_operation_attempts` | Web operation | In-request execution attempt/fence audit; future worker seam only | Durable worker lease, automatic retry, provider job or billing attempt |
| `web_video_operation_events` | Web operation | Ordered lifecycle evidence | Bot audit log, payment ledger, webhook, notification or delivery receipt |

These are additive schema records. They do not migrate, synchronize, infer or
overwrite any Bot table. The Bot remains the canonical writer for its own
identity, wallet, PayOS, jobs and provider state.

No destructive migration or schema synchronization is authorized by this inventory.
