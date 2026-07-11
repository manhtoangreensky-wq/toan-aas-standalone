# Bot-to-Web inventory

| Area | Bot | Web App |
| --- | --- | --- |
| Commands | 786 | Mapped through feature/route registry |
| Callbacks | 55 | Mapped or explicitly TELEGRAM_ONLY |
| Conversations | 0 | Draft/estimate/confirm contract |
| FastAPI routes | 169 | 143 |
| DB tables | 97 | 43 |

Canonical business state remains in the bot; this inventory never imports runtime code.
