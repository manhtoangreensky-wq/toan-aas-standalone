# ShopAI confirmation callback contract

The frozen Bot owns the `shopai|*` callback handler. Its only observed templates are `confirm`, `package` and `cancel` with one opaque token. The handler requires exactly three callback parts, resolves the token against a short-lived pending confirmation tied to `query.from_user.id`, rejects wrong/expired/replayed tokens and consumes a valid record before continuing. Confirm/package can enter canonical Xu, package, provider, job, payment, output and refund guards; cancel records a Bot-side cancellation for that same pending confirmation. This is not a Web top-up, browser checkout, browser cancel/back/reset, asset, job identifier or delivery contract.

| Frozen Bot callback source | Web target/boundary | Audit resolution | Required boundary |
| --- | --- | --- | --- |
| shopai\|cancel\|{*}, shopai\|confirm\|{*}, shopai\|package\|{*} | TELEGRAM_ONLY | bot_shopai_confirmation_requires_canonical_bot_state | opaque token is bound to a Telegram user, expires and is consumed by canonical Bot confirmation/package/cancel handling |
| case variants, missing token, suffixes or other shopai\|* values | SHOPAI_SOURCE_REVIEW_REQUIRED | shopai_callback_requires_exact_source_review | no Web wallet/top-up route, browser navigation/reset, provider/job/Xu/payment/output/delivery action or runtime claim |

Only the exact lowercase templates in this table retain the Bot-only disposition. Every case variant, missing token, suffix and future `shopai|*` value resolves to `SHOPAI_SOURCE_REVIEW_REQUIRED`. It cannot navigate to `/wallet/topup`, create/approve/finalize a payment, mutate Xu, invoke a provider, create/retry/cancel/refund a job, reset browser state, expose an output or claim delivery. A future Web-native ShopAI-like capability must start from a separately designed signed owner-scoped contract with independently recomputed price/authorization/idempotency; it must not accept or replay a Telegram token.
