# PayOS, wallet, and jobs boundary

- Canonical writer: Telegram bot.
- Web App role: signed-session caller of the private bridge; it must never credit Xu, finalize PayOS, or add a second payment webhook.
- Manual top-up is a Telegram Bot-only handoff until a separate read-only,
  owner-scoped and redacted `pending_deposits` bridge contract exists. Web
  must not receive bills/TXIDs, create requests, run review actions or infer
  approval from a browser event.
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
