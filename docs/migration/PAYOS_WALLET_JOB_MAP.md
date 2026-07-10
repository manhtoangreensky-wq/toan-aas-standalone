# PayOS, wallet and job safety map

- One canonical PayOS webhook and wallet writer: Telegram bot.
- Web never calculates credit, finalizes redirect, stores a second order ledger, or exposes payment secrets.
- Manual top-up stays a Bot handoff: the P0 bridge has no owner-scoped, redacted `pending_deposits` history adapter. Web must not accept bills/TXIDs, create a manual request, approve/reject it or claim a result before canonical wallet history reflects an approved Bot transaction.
- Job completion means validated output bytes or a canonical queued task with a polling route; HTTP success alone is insufficient.
- Retry/refund/freeze remain guarded until their existing canonical bot action has a tested adapter.
