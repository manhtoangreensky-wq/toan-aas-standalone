# Known gaps from static audit

| Area | Severity | Count | Finding |
| --- | --- | --- | --- |
| customer_and_admin_routes | high | 0 | Bot source mappings that do not have an observed Web App route or guarded compatibility surface. |
| private_core_bridge | high | 1 | Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. Current checkout contract status: BOT_BRIDGE_SOURCE_MISSING |
| telegram_bot_to_web_identity_callback | high | 1 | Direction-specific one-time Telegram callback contract. Current checkout status: CALLBACK_CONTRACT_GAPS_FOUND |
| database_authority | high | 86 | Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers. |
| feature_surface | medium | 0 | Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface. |

These are static findings. Resolve each through contracts and tests before marking a Web App flow complete.
