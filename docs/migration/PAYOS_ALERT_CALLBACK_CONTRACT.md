# PayOS alert callback disposition contract

The frozen Bot emits the finite `payosalert` callbacks only from owner/admin PayOS alert keyboards, and `handle_payos_alert_callback` rejects a non-admin caller before it reads the action. These are not customer wallet/top-up controls and no value below transfers a Telegram message ID, a Bot-local mute window, a manual-bill state, a provider diagnostic, a PayOS registration state, or an environment value into the Web App.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| payosalert\|manual | /admin/payments | reviewed_payos_alert_admin_navigation | NAVIGATION_ONLY | BOT_ADMIN_ONLY, BOT_EPHEMERAL_BILL_STATE_NOT_REPLAYED, FRESH_SIGNED_WEB_ADMIN_NAVIGATION, NO_RUNTIME_CLAIM |
| payosalert\|test | TELEGRAM_ONLY | reviewed_payos_alert_telegram_admin_only | TELEGRAM_ONLY | BOT_ADMIN_ONLY, TELEGRAM_COMMAND_GUIDANCE, NO_RUNTIME_CLAIM |
| payosalert\|mute | TELEGRAM_ONLY | reviewed_payos_alert_telegram_admin_only | TELEGRAM_ONLY | BOT_ADMIN_ONLY, BOT_PROCESS_LOCAL_ALERT_STATE, NO_RUNTIME_CLAIM |
| payosalert\|renewed | TELEGRAM_ONLY | reviewed_payos_alert_telegram_admin_only | TELEGRAM_ONLY | BOT_ADMIN_ONLY, DEPLOYMENT_ENV_GUIDANCE, NO_RUNTIME_CLAIM |
| payosalert\|remind_later | TELEGRAM_ONLY | reviewed_payos_alert_telegram_admin_only | TELEGRAM_ONLY | BOT_ADMIN_ONLY, TELEGRAM_MESSAGE_DISMISSAL, NO_RUNTIME_CLAIM |
| other payosalert\|* | PAYOS_ALERT_SOURCE_REVIEW_REQUIRED | payos_alert_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | BOT_ADMIN_ONLY, CANONICAL_BOT_PAYOS_ALERT_FLOW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

`payosalert|manual` is the sole navigation-only exception: it opens a fresh signed, role-checked `/admin/payments` view. It does not create a payment, request a manual top-up, expose a customer route, carry Bot `USER_BILL_STATE`, add Xu, finalize PayOS, call a provider, change an environment variable, or create a webhook/ledger. `test`, `mute`, `renewed`, and `remind_later` stay Telegram-only until a separately reviewed, canonical admin contract exists.

An unlisted `payosalert|*` value is deliberately unresolved. It must be source-reviewed before it can become a Web route, bridge method, payment action, diagnostics control, alert preference, or deployment setting.
