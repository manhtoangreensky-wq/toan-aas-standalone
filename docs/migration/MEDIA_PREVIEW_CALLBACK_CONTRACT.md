# Dynamic media-preview callback disposition contract

The Bot emits these dynamic music/SFX and media-library preview callbacks only from its Telegram media-preview keyboards. Their formatted values are a media kind/index pair or short-lived cache index, not an owner-scoped Web asset, catalog record, playback authorization, media license verification, or downstream Web media-selection contract. Every entry remains `NEEDS_FEATURE_DISPOSITION`; its target is a symbolic Bot authority boundary, **not** a Web route, browser callback, bridge implementation, provider action, wallet/payment action, job action, asset claim, or output-delivery claim.

| Bot callback template | Required authority boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| play_{*}\|{*} | BOT_MEDIA_PREVIEW_CACHE_AND_TELEGRAM_DELIVERY_REQUIRED | media_preview_play_requires_bot_cache_and_telegram_delivery | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_DELIVERY, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| select_{*}\|{*} | BOT_MEDIA_PREVIEW_CACHE_AND_SELECTION_STATE_REQUIRED | media_preview_select_requires_bot_cache_and_selection_state | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, BOT_MEDIA_SELECTION_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| license_{*}\|1 | BOT_MEDIA_PREVIEW_CACHE_AND_TELEGRAM_GUIDANCE_REQUIRED | media_preview_license_requires_bot_cache_and_telegram_guidance | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_GUIDANCE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| license_music\|{*} | BOT_MEDIA_PREVIEW_CACHE_AND_TELEGRAM_GUIDANCE_REQUIRED | media_preview_license_requires_bot_cache_and_telegram_guidance | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_GUIDANCE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| play_media\|{*} | BOT_MEDIA_PREVIEW_CACHE_AND_TELEGRAM_DELIVERY_REQUIRED | media_preview_play_requires_bot_cache_and_telegram_delivery | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_DELIVERY, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| select_media\|{*} | BOT_MEDIA_PREVIEW_CACHE_AND_SELECTION_STATE_REQUIRED | media_preview_select_requires_bot_cache_and_selection_state | NEEDS_FEATURE_DISPOSITION | BOT_MEDIA_PREVIEW_CACHE, BOT_MEDIA_SELECTION_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

A future Web media experience must begin from independently verified catalog/media data and an owner-scoped reference. It must not accept a Bot cache index, replay the Telegram callback, read Bot selected-media state, claim license clearance, or trigger a Bot/video/provider action.
