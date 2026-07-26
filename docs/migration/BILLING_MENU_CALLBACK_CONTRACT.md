# Billing menu callback disposition contract

The 2 exact Bot menu values below are administrator-only Billing guidance. They are not customer wallet/top-up entries, browser commands, payment/order references, canonical ledger rows or settlement state. The standalone Web never receives a raw callback token, Telegram identity, Bot menu/context, pending deposit, manual bill, bill ID, payment reference, wallet/Xu balance, PayOS/webhook state, provider state or write authority.

| Bot callback source | Fresh Web target | Audit resolution | Status | Audience | Authority | Source dispositions |
| --- | --- | --- | --- | --- | --- | --- |
| menu\|billing | /admin/payments | reviewed_billing_menu_admin_navigation | NAVIGATION_ONLY | admin | SIGNED_CANONICAL_ADMIN_READ | BOT_ADMIN_ONLY, BOT_BILLING_MENU_STATE_NOT_REPLAYED, FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION, NO_CUSTOMER_OR_MANUAL_TOPUP_ACTION, NO_PAYOS_WALLET_OR_LEDGER_ACTION, NO_RUNTIME_CLAIM |
| menu\|admin_billing_pending | /admin/payments | reviewed_billing_menu_admin_navigation | NAVIGATION_ONLY | admin | SIGNED_CANONICAL_ADMIN_READ | BOT_ADMIN_ONLY, BOT_BILLING_PENDING_HELP_NOT_REPLAYED, FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION, NO_BILL_ID_OR_PAYMENT_REFERENCE_TRANSFER, NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION, NO_PAYOS_WALLET_OR_LEDGER_ACTION, NO_RUNTIME_CLAIM |

Each reviewed disposition starts a **fresh**, independently signed and canonical-role-checked `/admin/payments` read route. It is navigation only: it does not create a payment, accept a manual top-up/bill/TXID, expose a customer route, debit/credit Xu, finalize PayOS, call a provider, register a webhook, write an order/ledger/refund or claim any runtime result. `menu|admin_billing_duyet` remains source-review-required; `menu|admin_billing_tuchoi` remains source-review-required; and `menu|admin_billing_payos` remains source-review-required. Any other `menu|billing*` or `menu|admin_billing*` value cannot inherit this Admin route.
