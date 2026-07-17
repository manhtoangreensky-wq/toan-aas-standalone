# Known gaps and guards

| Area | Severity | Count | Finding |
| --- | --- | --- | --- |
| customer_and_admin_routes | high | 0 | Bot source mappings that do not have an observed Web App route or guarded compatibility surface. |
| dynamic_callback_templates | high | 0 | Only templates without a manually reviewed namespace-to-workflow route remain unresolved. A resolved template proves a guarded route family, never a dynamic value or runtime execution. |
| private_core_bridge | high | 1 | Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. Current checkout contract status: BOT_BRIDGE_SOURCE_MISSING |
| telegram_bot_to_web_identity_callback | high | 1 | Direction-specific one-time Telegram callback contract. Current checkout status: CALLBACK_CONTRACT_GAPS_FOUND |
| database_authority | high | 86 | Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers. |
| feature_surface | medium | 0 | Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface. |

A guarded feature remains visible with safe Vietnamese copy and must not call a provider or claim an output.
