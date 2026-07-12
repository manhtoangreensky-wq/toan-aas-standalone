# Historical prototype note — do not use as runtime configuration

The former standalone Web billing routes described in this document were
retired. They are not mounted by `app.py`, and `main.py` now exports the same
safe ASGI app as Railway.

Current source of truth is
[PAYOS_WALLET_JOB_MAP.md](../migration/PAYOS_WALLET_JOB_MAP.md):

- Telegram Bot is the sole PayOS order creator, webhook receiver and Xu writer.
- Web uses a signed private bridge only after it receives a dedicated canonical
  top-up SKU catalog.
- A Bot-issued checkout URL is rendered only after strict HTTPS + PayOS-host
  validation and is not stored by the Web App.
- Manual top-up proof, TXID, bank account, QR and approval remain inside the
  Bot `/thucong` conversation.

Do not configure `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, or
`PAYOS_CHECKSUM_KEY` in this Web App for the retired prototype routes.
