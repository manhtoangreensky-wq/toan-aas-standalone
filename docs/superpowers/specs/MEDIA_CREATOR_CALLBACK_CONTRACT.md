# Media Creator residual callback contract

The frozen Bot dispatches `create_media|*` through one Telegram Media Creator handler. Its residual actions can redraw Telegram menus, clear per-user pending state, select media/tier/aspect, consume confirmation state, inspect guards, or enter a provider/job/payment path. They are not browser controls or Web feature launches.

| Frozen Bot callback family | Web target/boundary | Audit resolution | Status | Required boundary |
| --- | --- | --- | --- | --- |
| all other create_media\|* literals/templates, including main/support/pricing/trend, image/video tier/aspect and generic add/skip/choice/confirm patterns | MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED | media_creator_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | no Web route, browser reset/history action, provider/job/wallet/payment/output/delivery claim |

Exact `create_media|cancel` is covered separately by `MEDIA_CREATOR_CANCEL_CALLBACK_CONTRACT.md`. Only the finite lowercase Quick Image literals/templates in `QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md` retain their own fresh Planner or canonical Bot-only dispositions. Every remaining case variant, suffix, tier/aspect, menu, support/pricing/trend or future `create_media|*` source must receive an explicit Web-native contract before it may gain any browser meaning. In particular it never becomes `/media-factory`, `/membership`, a video feature route, browser back/reset, provider/job/wallet/PayOS action, output, asset or delivery claim.
