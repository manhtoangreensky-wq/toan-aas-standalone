# Bot-to-Web inventory

| Area | Bot | Web App |
| --- | --- | --- |
| Commands | 773 | Mapped through feature/route registry |
| Callback dispatcher registrations | 54 | Source provenance only; not a feature/action mapping |
| Concrete callback values | 2841 | Mapped, guarded, actionable backlog or TELEGRAM_ONLY |
| Conversations | 0 | Draft/estimate/confirm contract |
| FastAPI routes | 139 | 640 |
| DB tables | 97 | 209 |

Canonical business state remains in the bot; this inventory never imports runtime code.
