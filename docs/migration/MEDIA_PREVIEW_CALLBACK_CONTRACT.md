# Dynamic media-preview callback disposition contract

The Bot emits these dynamic music/SFX and media-library preview callbacks only from its Telegram media-preview keyboards. Their formatted values are a media kind/index pair or short-lived cache index, not an owner-scoped Web asset, catalog record, playback authorization, media license verification, or downstream Web media-selection contract. Every original Bot callback is explicitly `TELEGRAM_ONLY`: it neither becomes a browser callback nor carries its cache index into Web. The independently owned Web Media Workspace may preview an account's separately attached Asset Vault audio reference when its dedicated feature flag is enabled; it does not consume Bot cache, selected-media state, provider results or Telegram delivery state.

| Bot callback template | Required authority boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| play_{*}\|{*} | TELEGRAM_ONLY | reviewed_bot_preview_play_telegram_only_web_owned_preview_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_DELIVERY, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| select_{*}\|{*} | TELEGRAM_ONLY | reviewed_bot_media_select_telegram_only_web_owned_reference_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, BOT_MEDIA_SELECTION_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| license_{*}\|1 | TELEGRAM_ONLY | reviewed_bot_media_license_telegram_only_web_rights_note_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_GUIDANCE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| license_music\|{*} | TELEGRAM_ONLY | reviewed_bot_media_license_telegram_only_web_rights_note_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_GUIDANCE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| play_media\|{*} | TELEGRAM_ONLY | reviewed_bot_preview_play_telegram_only_web_owned_preview_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, TELEGRAM_CHAT_DELIVERY, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |
| select_media\|{*} | TELEGRAM_ONLY | reviewed_bot_media_select_telegram_only_web_owned_reference_separate | TELEGRAM_ONLY | BOT_MEDIA_PREVIEW_CACHE, BOT_MEDIA_SELECTION_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

A future Web media experience must begin from independently verified catalog/media data and an owner-scoped reference. It must not accept a Bot cache index, replay the Telegram callback, read Bot selected-media state, claim license clearance, or trigger a Bot/video/provider action.
