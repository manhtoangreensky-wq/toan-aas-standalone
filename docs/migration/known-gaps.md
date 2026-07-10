# Known gaps from static audit

| Area | Severity | Count | Finding |
| --- | --- | --- | --- |
| customer_and_admin_routes | high | 0 | Bot source mappings that do not have an observed Web App route or guarded compatibility surface. |
| private_core_bridge | high | 0 | Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. |
| database_authority | high | 86 | Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers. |
| feature_surface | medium | 0 | Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface. |

These are static findings. Resolve each through contracts and tests before marking a Web App flow complete.
