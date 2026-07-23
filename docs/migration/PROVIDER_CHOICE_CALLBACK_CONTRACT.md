# Provider choice callback contract

The frozen Bot owns the `prov|*` callback handler. Each reviewed callback carries exactly a service, mode and Telegram uid. The handler verifies that uid against the Telegram caller, consumes a short-lived `USER_PENDING` voice/image request, and can cancel with a canonical Xu refund or continue through canonical charge/refund, provider/fallback and Telegram media delivery. It is not a Web image/voice route, browser choice, Web-owned quote, provider request, job identifier, asset, checkout, wallet record or delivery contract.

| Frozen Bot callback source | Web target/boundary | Audit resolution | Required boundary |
| --- | --- | --- | --- |
| prov\|cancel\|cancel\|{*}, prov\|image\|free\|{*}, prov\|image\|paid\|{*}, prov\|voice\|free\|{*}, prov\|voice\|paid\|{*} | TELEGRAM_ONLY | bot_provider_choice_requires_canonical_pending_state | Telegram uid plus a consumed pending voice/image request; canonical Xu charge/refund, provider/fallback and Telegram output delivery remain Bot-only |
| case variants, missing token, suffixes or other prov\|* values | PROVIDER_CHOICE_SOURCE_REVIEW_REQUIRED | provider_choice_callback_requires_exact_source_review | no Web image/voice/wallet route, browser navigation/reset, provider/job/payment/output/delivery action or runtime claim |

Only exact lowercase templates in this table retain the Bot-only disposition. Every case variant, missing token, suffix and future `prov|*` value resolves to `PROVIDER_CHOICE_SOURCE_REVIEW_REQUIRED`. It cannot open `/image`, `/voice-vault` or `/wallet/topup`; navigate/reset the browser; accept a Telegram uid or pending request; invoke a provider; charge/refund Xu; create/retry/refund a job; expose an output or claim delivery. A future Web-native image or voice workflow must begin from its own signed owner-scoped draft, independently recomputed authorization/price and idempotent provider-job contract. It must never accept or replay a Telegram provider-choice callback.
