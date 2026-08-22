# Video-job callback disposition contract

The frozen Bot emits these `job` callbacks only from its admin-only video-job keyboard. Its callback handler rejects a non-admin caller before it reads the action. The `stats` branch only reads canonical Bot campaign/video-job rows and redraws a Telegram message. The `approve` and `cancel` branches resolve a canonical job ID against the Bot owner before updating the canonical job status.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| job\|stats\|0 | /admin/jobs | reviewed_video_job_stats_admin_navigation | NAVIGATION_ONLY | BOT_ADMIN_ONLY, BOT_VIDEO_JOB_STATS_NOT_REPLAYED, FRESH_SIGNED_WEB_ADMIN_NAVIGATION, NO_RUNTIME_CLAIM |
| job\|approve\|{*} | TELEGRAM_ONLY | bot_canonical_video_job_mutation | TELEGRAM_ONLY | BOT_ADMIN_ONLY, CANONICAL_BOT_JOB_MUTATION, OWNER_SCOPED_BOT_JOB_REQUIRED, NO_RUNTIME_CLAIM |
| job\|cancel\|{*} | TELEGRAM_ONLY | bot_canonical_video_job_mutation | TELEGRAM_ONLY | BOT_ADMIN_ONLY, CANONICAL_BOT_JOB_MUTATION, OWNER_SCOPED_BOT_JOB_REQUIRED, NO_RUNTIME_CLAIM |
| other job\|* | BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED | video_job_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | BOT_ADMIN_ONLY, CANONICAL_BOT_VIDEO_JOB_STATE, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

`job|stats|0` is the sole navigation-only exception: it may open a fresh signed, role-checked `/admin/jobs` surface. It transfers no Telegram identity, Bot job ID, campaign/video-job row, cached result, provider state, output/delivery claim, or mutation into the browser. `/admin/jobs` must use its own canonical admin authorization and remain guarded if its bridge projection is unavailable.

`job|approve|{*}` and `job|cancel|{*}` stay Telegram-only. The Web must not accept a Bot job ID, approve/cancel a canonical job, infer runtime completion, call a provider, debit/credit Xu, finalize PayOS, or create a second job state machine. Any unlisted `job|*` value is source-review-required.
