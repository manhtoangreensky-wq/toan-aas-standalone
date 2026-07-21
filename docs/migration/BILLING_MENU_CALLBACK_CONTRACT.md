# Billing menu callback disposition contract

The frozen Bot callback handler treats the exact `menu|billing` value as administrator-only, even though a top-up keyboard may render a billing button. Its protected branch can show Bot-local billing and manual-payment guidance. It is not a customer wallet/top-up entry, a browser command, a payment/order reference, a canonical ledger row or a settlement state. The standalone Web never receives the raw callback token, a Telegram identity, Bot menu/context, pending deposit, manual bill, payment reference, wallet/Xu balance, PayOS/webhook state, provider state or write authority.

| Bot callback source | Fresh Web target | Audit resolution | Status | Audience | Authority | Source dispositions |
| --- | --- | --- | --- | --- | --- | --- |
| menu\|billing | /admin/payments | reviewed_billing_menu_admin_navigation | NAVIGATION_ONLY | admin | SIGNED_CANONICAL_ADMIN_READ | BOT_ADMIN_ONLY, BOT_BILLING_MENU_STATE_NOT_REPLAYED, FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION, NO_CUSTOMER_OR_MANUAL_TOPUP_ACTION, NO_PAYOS_WALLET_OR_LEDGER_ACTION, NO_RUNTIME_CLAIM |

The sole reviewed disposition starts a **fresh**, independently signed and canonical-role-checked `/admin/payments` read route. It is navigation only: it does not create a payment, accept a manual top-up/bill/TXID, expose a customer route, debit/credit Xu, finalize PayOS, call a provider, register a webhook, write an order/ledger/refund or claim any runtime result. Any other `menu|billing*` value remains source-review-required and cannot inherit this Admin route.
