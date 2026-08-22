# Storage add-on callback disposition contract

The frozen Bot storage add-on flow is a Telegram conversation, not a Xu top-up. Its menu draws a Bot-owned storage catalog; its custom branch stores a short-lived pending action for the Telegram user and expects a following Telegram message; and its confirmation branch validates a Bot catalog spec, can create a canonical storage order and PayOS checkout, then grants quota only after canonical settlement.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| storage\|menu | TELEGRAM_ONLY | reviewed_storage_addon_telegram_only | TELEGRAM_ONLY | CANONICAL_BOT_STORAGE_ADDON_CATALOG, TELEGRAM_PAYMENT_CONTEXT, NO_RUNTIME_CLAIM |
| storage\|custom | TELEGRAM_ONLY | reviewed_storage_addon_telegram_only | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, BOT_PENDING_STORAGE_INPUT, NO_RUNTIME_CLAIM |
| storage\|confirm\|{*} | TELEGRAM_ONLY | bot_canonical_storage_addon_checkout | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, CANONICAL_BOT_STORAGE_ORDER_REQUIRED, CANONICAL_BOT_PAYOS_CHECKOUT, CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT, NO_RUNTIME_CLAIM |
| other storage\|* | STORAGE_ADDON_SOURCE_REVIEW_REQUIRED | storage_addon_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

No value above becomes `/wallet/topup`, a Web amount/code, a browser checkout, a Web storage ledger, a second PayOS webhook, or a quota grant. The Web may later add a separately reviewed owner-scoped Storage Center and bridge contract, but it must start from canonical current state rather than replay a Bot callback or Telegram pending value.

Any unlisted `storage|*` value remains source-review-required. It must not create an order, call PayOS, grant quota, write storage usage, call a provider, or claim that a storage purchase succeeded.
