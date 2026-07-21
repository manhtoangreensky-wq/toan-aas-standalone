# Main Guide callback contract

The frozen Bot Main Guide is a Telegram information menu. Its child buttons can enter Bot-local conversations, pending media, provider/output guards, canonical Xu/package/PayOS paths, or support context. The standalone Web never receives the callback token, Telegram identity, guide prose, child button, message, pending value, Bot job/asset, provider state, wallet mutation, payment state or output claim.

| Frozen Bot guide action | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| menu\|guide_quick_start | /features | reviewed_guided_start_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_GUIDED_START, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|guide_faq | /support | reviewed_guided_start_fresh_web_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_SUPPORT_NAVIGATION, BOT_FAQ_REFUND_OR_SUPPORT_CONTEXT_NOT_REPLAYED, NO_RAW_TELEGRAM_ID_BROWSER_INPUT, NO_RUNTIME_CLAIM |
| menu\|guide_image_ai | /image-studio | reviewed_exact_menu_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|guide_music_add | /media-workspace | reviewed_exact_menu_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|guide_credits | /wallet | reviewed_exact_menu_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|support | /support | reviewed_exact_menu_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|main | /dashboard | reviewed_exact_menu_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| menu\|guide_guided_video | GUIDED_VIDEO_MENU_DEFERRED | guided_video_menu_deferred_until_video_menu_phase | NEEDS_FEATURE_DISPOSITION | BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED, VIDEO_MENU_LAST, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| menu\|guide_video_ai | GUIDED_VIDEO_MENU_DEFERRED | guided_video_menu_deferred_until_video_menu_phase | NEEDS_FEATURE_DISPOSITION | BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED, BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED, VIDEO_MENU_LAST, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

`menu|guide_quick_start` starts the signed Web catalog at `/features`; it is navigation only, not a wizard execution. `menu|guide_faq` starts the signed Support Desk, which uses the Web account and owner-scoped ticket contract rather than a raw Telegram-ID field, Bot chat transcript, screenshot, refund request or status. The pre-existing image, music and canonical wallet navigation entries also begin fresh Web pages and carry no Telegram context.

`menu|guide_video_ai` and `menu|guide_guided_video` are intentionally **not** routed to Dashboard or a generic Video page. They remain visible migration backlog records until the final finite Video menu phase can define an independently signed, owner-scoped Web contract without replaying the Bot state machine.
