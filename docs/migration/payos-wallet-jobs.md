# PayOS, wallet, and jobs boundary

- Canonical writer: Telegram bot.
- Web App role: signed-session caller of the private bridge; it must never credit Xu, finalize PayOS, or add a second payment webhook.
- Manual top-up is a Telegram Bot-only handoff until a separate read-only, owner-scoped and redacted `pending_deposits` bridge contract exists. Web must not receive bills/TXIDs, create requests, run review actions or infer approval from a browser event. `manual|*` callback values are a separate canonical Bot boundary; see `MANUAL_PAYMENT_CALLBACK_CONTRACT.md`.
- Provider choice is a Telegram Bot-only handoff: `prov|*` binds a Telegram user to a consumed pending voice/image request and may charge/refund Xu, invoke a provider/fallback and deliver media in Telegram. It cannot open a Web route or execute a browser provider/output action; see `PROVIDER_CHOICE_CALLBACK_CONTRACT.md`.
- Bot Image Tools callbacks are a Telegram state-machine boundary: `imgtool|*` can use pending/result/file/prompt/note state, local output, ShopAI tier/confirmation, provider/Xu and Telegram delivery. Web must not route or replay them; see `IMAGE_TOOLS_CALLBACK_CONTRACT.md`.
- Bot Support/Ticket callbacks are a Telegram owner/role workflow boundary: `support|*` and `ticket|*` can use support/lead/ticket/attachment/pending state and Bot admin reply/delivery controls. Web must not route or replay them; see `SUPPORT_TICKET_CALLBACK_CONTRACT.md`.
- Provider/payments remain disabled in local/test unless an explicit feature flag and approved integration are present.

## Related bot tables detected statically

- `credit_events`
- `local_worker_jobs`
- `media_factory_jobs`
- `music_generation_jobs`
- `payos_orders`
- `payos_processed`
- `production_jobs`
- `publish_jobs`
- `shopaikey_jobs`
- `transactions`
- `video_jobs`
- `video_script_jobs`

Completion must remain conditional on validated output, not a pending/provider acknowledgement.
