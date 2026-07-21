# Quick Image Planner callback contract

The frozen Bot Quick Image conversation contains a non-executing draft grammar followed by a canonical tier/ShopAI confirmation path. The standalone Web Planner is a fresh signed, CSRF-protected deterministic prompt-plan surface at `/image/quick-planner`; it does not import Bot state, expose raw callbacks, or execute an image workflow.

| Frozen Bot source | Web target/boundary | Audit resolution | Required boundary |
| --- | --- | --- | --- |
| create_media\|quick_image, qi_entry, qi_suggest, qi_refresh, qi_pick_1..3, qi_custom, qi_rewrite, qi_topics, qi_back_suggestions | /image/quick-planner | reviewed_quick_image_planner_fresh_web_draft | fresh signed draft only; no Telegram state/callback is transferred |
| create_media\|qi_logo_choice, qi_logo_add, qi_logo_skip, qi_logo_confirm, qi_logo_pos\|{top_left…bottom_right} | /image/quick-planner | reviewed_quick_image_planner_fresh_web_draft | text-only direction and nine semantic placements; no logo upload/overlay/image output |
| create_media\|qi_choose_ratio, qi_ratio_{*}, qi_back_prompt, qi_back_ratio | /image/quick-planner | reviewed_quick_image_planner_fresh_web_draft | finite prompt/ratio plan; no tier, quote or execution |
| create_media\|qi_back_tier, qi_tier_{*} | TELEGRAM_ONLY | bot_quick_image_tier_or_confirm_requires_canonical_bot_state | Bot tier/one-time confirmation state and canonical Xu/provider/job boundary |
| shopai\|confirm\|{*}, shopai\|package\|{*} | TELEGRAM_ONLY | bot_quick_image_tier_or_confirm_requires_canonical_bot_state | opaque canonical checkout/confirmation; no browser payment, ledger, job or delivery action |

The static auditor derives the nine `qi_logo_pos` values only from the direct frozen helper call that supplies the literal Quick Image prefix. It does not map the helper's shared dynamic `create_media|{*}|…` template globally because regular image/video flows also use it.

The Web request accepts only a finite catalog key or an original bounded custom brief, deterministic variation, ratio, optional text brand direction and placement, and locale. It has no image upload, preview, source analysis, provider/Bot/Core Bridge call, tier, quote, confirmation token, job, asset, Xu/wallet mutation, PayOS payment, webhook, publish action or delivery. `prompt_plan_only_no_real_image` is a manual-review plan, not evidence that an image or watermark exists.
