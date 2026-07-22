# Media Creator cancellation callback contract

The frozen Bot accepts exactly `create_media|cancel` inside its Media Creator callback handler. That branch clears a broad set of short-lived per-Telegram-user pending buckets, then replaces the Telegram message with a Bot main-menu callback. It does not identify one Web draft, a browser route, browser history, or a Web session scope.

| Frozen Bot callback | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| create_media\|cancel | TELEGRAM_ONLY | reviewed_media_creator_cancel_requires_bot_local_pending_state | TELEGRAM_ONLY | TELEGRAM_CALLBACK_CONTEXT, TELEGRAM_IDENTITY_CONTEXT, BOT_MEDIA_CREATOR_BROAD_PENDING_STATE_CLEARING, BOT_SHOPAI_CONFIRMATION_TOKEN_STATE, BOT_PENDING_CONTEXT_NOT_REPLAYED, TELEGRAM_MESSAGE_REPLACEMENT, NO_WEB_GLOBAL_DRAFT_SESSION_OR_HISTORY_RESET, NO_WEB_NAVIGATION_OR_BROWSER_ACTION, NO_BOT_OR_WEB_JOB_CANCELLATION_REPLAY, NO_JOB_WALLET_PAYMENT_PROVIDER_OR_DELIVERY_ACTION, NO_RUNTIME_CLAIM |
| other create_media\|cancel* | MEDIA_CREATOR_CANCEL_SOURCE_REVIEW_REQUIRED | media_creator_cancel_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_CREATOR_CANCEL_OR_PENDING_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_WEB_GLOBAL_DRAFT_SESSION_OR_HISTORY_RESET, NO_WEB_NAVIGATION_OR_BROWSER_ACTION, NO_RUNTIME_CLAIM |

The reviewed literal is **not** a browser cancel, back or reset action. The standalone Web must not navigate to a dashboard, mutate a global draft/session, clear unrelated Web state, replay the Telegram message, invoke a provider/job/payment operation, or claim that any external work was cancelled. A Web-native workflow may define its own scoped cancel control only from its own signed draft contract. Case variants, suffixes and future `create_media|*` values remain source-review-required and cannot inherit this Bot-only disposition.
