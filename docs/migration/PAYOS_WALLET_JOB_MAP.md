# PayOS, wallet and job safety map

- One canonical PayOS webhook and wallet writer: Telegram bot.
- Web never calculates credit, finalizes redirect, stores a second order ledger, or exposes payment secrets.
- Manual top-up stays a Bot handoff: the P0 bridge has no owner-scoped, redacted `pending_deposits` history adapter. Web must not accept bills/TXIDs, create a manual request, approve/reject it or claim a result before canonical wallet history reflects an approved Bot transaction.
- The Bot's `payosalert|*` controls are admin-alert callbacks, not customer billing controls. Only the source-reviewed `manual` value may open a fresh signed `/admin/payments` view; it cannot replay Bot bill state or execute a payment action. See `PAYOS_ALERT_CALLBACK_CONTRACT.md`.
- Service package/combo checkout is distinct from Xu top-up. The Web can only open its fresh read-only `/packages` catalog for nine reviewed Bot selectors; its confirm callback stays Bot-only, and `POST /payments/create` must not accept a service package. See `PACKAGE_PURCHASE_CALLBACK_CONTRACT.md`.
- Bot video-job stats can only open a fresh signed `/admin/jobs` view for one reviewed admin callback. Canonical approve/cancel actions stay Telegram-only until a dedicated owner-scoped admin bridge exists; the Web never accepts a Bot job ID. See `VIDEO_JOB_CALLBACK_CONTRACT.md`.
- Job completion means validated output bytes or a canonical queued task with a polling route; HTTP success alone is insufficient.
- Retry/refund/freeze remain guarded until their existing canonical bot action has a tested adapter.
