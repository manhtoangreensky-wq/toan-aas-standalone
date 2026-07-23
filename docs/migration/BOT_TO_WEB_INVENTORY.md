# Bot-to-Web inventory

| Area | Bot | Web App |
| --- | --- | --- |
| Commands | 773 | Mapped through feature/route registry |
| Callback dispatcher registrations | 54 | Source provenance only; not a feature/action mapping |
| Concrete callback values | 2862 | Mapped, guarded, actionable backlog or TELEGRAM_ONLY |
| Conversations | 0 | Draft/estimate/confirm contract |
| FastAPI routes | 139 | 641 |
| DB tables | 97 | 212 |

Canonical business state remains in the bot; this inventory never imports runtime code.
