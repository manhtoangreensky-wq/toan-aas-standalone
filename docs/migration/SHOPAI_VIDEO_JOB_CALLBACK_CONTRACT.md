# ShopAI Video Job callback contract

The frozen Bot owns the `shopai_video_job|*` callback handler. Its observed callback forms either redraw the Telegram main menu, resolve a task ID against canonical Bot ownership, display an admin-only provider status panel, poll the provider and update canonical job/error/result state, deliver a video in Telegram, or start a guarded retry that can enter billing/confirmation state. The callback is not a Web video/jobs route, a browser back/reset action, a Web-owned task identifier, an owner-scoped download, a read-only provider API or a safe retry operation.

| Frozen Bot callback source | Web target/boundary | Audit resolution | Required boundary |
| --- | --- | --- | --- |
| shopai_video_job\|main | TELEGRAM_ONLY | bot_shopai_video_job_requires_canonical_bot_state | redraws the Bot Telegram main menu; it is not a Web video route, browser back action or history reset |
| shopai_video_job\|retry\|{*}, shopai_video_job\|status\|{*}, shopai_video_job\|{*} | TELEGRAM_ONLY | bot_shopai_video_job_requires_canonical_bot_state | opaque task/job identifier is resolved against canonical Bot ownership; provider poll, job/billing update, Telegram delivery and guarded retry remain Bot-only |
| case variants, bare values, suffixes or other shopai_video_job\|* values | SHOPAI_VIDEO_JOB_SOURCE_REVIEW_REQUIRED | shopai_video_job_callback_requires_exact_source_review | no Web top-up/jobs/video route, browser navigation/reset, provider/job/wallet/payment/output/delivery action or runtime claim |

Only exact lowercase forms in this table retain the Bot-only disposition. Every case variant, bare value, suffix and future `shopai_video_job|*` value resolves to `SHOPAI_VIDEO_JOB_SOURCE_REVIEW_REQUIRED`. It cannot open `/wallet/topup`, `/jobs` or a video page; navigate/reset the browser; poll a provider; mutate a job, Xu/package/payment/refund record; retry a job; expose an output or claim delivery. A future Web-native job center must begin from its own signed session and verified owner-scoped record through a separately reviewed bridge/read model; it must never accept or replay a Telegram task/job callback.
