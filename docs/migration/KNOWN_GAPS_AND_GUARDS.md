# Known gaps and guards

| Area | Severity | Count | Finding |
| --- | --- | --- | --- |
| customer_and_admin_routes | high | 0 | Bot source mappings that do not have an observed Web App route or guarded compatibility surface. |
| dashboard_navigation_fallbacks | high | 363 | Concrete Bot actions with no reviewed feature-family disposition are deliberately excluded from static Web-surface coverage and must be mapped to a Web-native workflow, a guarded runtime boundary, an admin-only contract, or TELEGRAM_ONLY. Callback dispatcher registrations are counted separately as source evidence. |
| callback_handler_dispatchers | high | 54 | CallbackQueryHandler registrations are recorded with their real handler identity and source line. They are Telegram transport evidence, not end-user browser actions, and are excluded from product-action coverage. |
| unreferenced_static_modules | high | 57 | Legacy handler-module records are retained as source evidence but excluded from the observed bot.py runtime parity denominator when the static import closure does not reach their module files. |
| dynamic_callback_templates | high | 45 | Only templates without a manually reviewed namespace-to-workflow route remain unresolved. A resolved template proves a guarded route family, never a dynamic value or runtime execution. |
| private_core_bridge | high | 1 | Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. Current checkout contract status: BOT_BRIDGE_SOURCE_MISSING |
| telegram_bot_to_web_identity_callback | high | 1 | Direction-specific one-time Telegram callback contract. Current checkout status: CALLBACK_CONTRACT_GAPS_FOUND |
| database_authority | high | 86 | Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers. |
| feature_surface | medium | 0 | Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface. |

A guarded feature remains visible with safe Vietnamese copy and must not call a provider or claim an output.

## Additive Web-native guard: Video Poster Lab

Video Poster Lab is a Web-owned, bounded private JPEG extraction utility, not
a Telegram command mapping. Its route, schema and read-model integration do
not make it live: it remains disabled until Asset Vault, the Video Operations
and Video Poster flags, an isolated private root, and trusted `ffmpeg` and
`ffprobe` are deliberately available together.

The request-time SQLite executor additionally requires an explicit
`WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica` acknowledgement. A
runtime with the feature enabled must attest a replica count of exactly `1`; a
missing, malformed or multi-replica deployment remains blocked.

The present executor is request-time only. It has no durable queue, retry
daemon, cross-replica coordination, long-form/video-series renderer or
provider/Bot fallback. On a missing runtime or interrupted attempt it must
fail closed instead of claiming an output. It does not change Bot authority
for Telegram identity, Bot jobs, provider state, Xu/wallet or PayOS. See
[`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md).
