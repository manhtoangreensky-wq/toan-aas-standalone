# TOAN AAS Standalone Web App

Production Web App for `app.toanaas.vn`.

## Runtime

- Railway entrypoint: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Compatibility entrypoint: `main:app` exports the exact same application.
- Health checks: `/health`, `/api/v1/health`
- Customer portal: `/dashboard`, `/projects`, `/project-packages`, `/asset-vault`, `/notes`, `/reminders`, `/inbox`, `/automation`, `/video-studio`, `/voice-studio`, `/wallet`, `/jobs`, `/assets`
- Admin Portal: `/admin` (signed session plus current canonical Bot role)

## Required Railway production configuration

- `WEB_SESSION_SECRET` is required: generate one long random value in the
  Railway **Variables** page. It signs Web sessions and must never be placed
  in Git, browser JavaScript, tickets or logs. The app intentionally refuses
  to start without it in production instead of issuing forgeable sessions.
- Web mailbox assurance and password recovery are separately opt-in. Leave
  WEBAPP_EMAIL_VERIFICATION_ENABLED and WEBAPP_PASSWORD_RECOVERY_ENABLED
  unset until a real authenticated SMTP transport and the HTTPS public origin
  are configured. Both use WEBAPP_EMAIL_SMTP_HOST, WEBAPP_EMAIL_SMTP_PORT,
  WEBAPP_EMAIL_SMTP_USERNAME, WEBAPP_EMAIL_SMTP_PASSWORD,
  WEBAPP_EMAIL_SMTP_TLS_MODE, WEBAPP_EMAIL_VERIFICATION_FROM and
  WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL. An enabled incomplete flow fails
  at startup rather than claiming delivery; see
  [Email Verification Contract](docs/migration/EMAIL_VERIFICATION_CONTRACT.md)
  and [Password Recovery Contract](docs/migration/PASSWORD_RECOVERY_CONTRACT.md).
- Web-native TOTP MFA is separately opt-in and defaults to guarded. Enable
  `WEBAPP_TOTP_MFA_ENABLED=true` only with a distinct Railway-only
  `WEBAPP_TOTP_MFA_ENCRYPTION_KEY` that is URL-safe base64 and decodes to
  exactly 32 bytes. It protects only the Web Email + password factor: no Bot
  identity, Xu, PayOS, provider, job or Telegram state is changed. An active
  factor fails closed if its runtime/key is unavailable. See
  [TOTP MFA Contract](docs/migration/TOTP_MFA_CONTRACT.md).
- Email/password login and registration also have a durable, Web-owned
  throttle in the same persistent session database. It stores only HMAC
  fingerprints of a normalized email and an effective client scope; never
  store or configure a raw email/IP list. The throttle uses
  `WEB_SESSION_SECRET` with domain separation by default; an operator may set
  a separate Railway-only `WEBAPP_AUTH_THROTTLE_HMAC_SECRET` during a planned
  key rotation. Leave `WEBAPP_AUTH_TRUSTED_PROXY_CIDRS` unset unless the
  direct Railway/reverse-proxy peer ranges are known exactly—otherwise
  `X-Forwarded-For` is intentionally ignored. See
  [`OAUTH_AUTH_MAP.md`](docs/migration/OAUTH_AUTH_MAP.md).
- Persist the Web-owned session database on the service's Railway volume. In
  `production`, `prod` **and** `live`, an explicit
  `WEBAPP_SESSION_DB_PATH` must resolve to a database file *under* the
  existing `RAILWAY_VOLUME_MOUNT_PATH` (or the standard persistent `/data`
  mount); an arbitrary absolute `/app/...` path is rejected at startup. See
  [`TELEGRAM_WEB_CONNECTION.md`](docs/migration/TELEGRAM_WEB_CONNECTION.md)
  for the full non-secret configuration contract.
- `WEBAPP_ASSET_VAULT_ENABLED` defaults to `false`. Enable it only after this
  **Web service** has a persistent volume. `WEBAPP_ASSET_VAULT_ROOT` must be
  an absolute child directory of that volume in production (for example
  `/data/toanaas_webapp_assets`); the application refuses static, relative or
  out-of-volume storage. The vault never serves blobs from `/static`.
- `WEBAPP_PROJECT_PACKAGE_ENABLED` defaults to `false`. Enable it only after
  this **Web service** has a persistent volume. Its
  `WEBAPP_PROJECT_PACKAGE_ROOT` must be a separate absolute child directory
  of that volume (for example `/data/toanaas_webapp_project_packages`), never
  `/static`, Asset Vault or its parent. See
  [`PROJECT_PACKAGE_CONTRACT.md`](docs/migration/PROJECT_PACKAGE_CONTRACT.md).
- `WEBAPP_DOCUMENT_OPERATIONS_ENABLED` defaults to `false`. PDF Split, PDF
  Merge, PDF Optimize, Image to PDF, PDF → images and PDF text → Word require
  Asset Vault **and** a separate persistent
  `WEBAPP_DOCUMENT_OPERATIONS_ROOT` (for example
  `/data/toanaas_webapp_document_operations`). It may not overlap Asset Vault,
  Project Package or `/static`; startup fails closed when the parser/runtime
  or private storage boundary is absent. Image to PDF also requires the
  separate opt-in `WEBAPP_IMAGE_TO_PDF_ENABLED=true` gate and its Pillow
  decoder runtime. PDF → images separately requires
  `WEBAPP_PDF_TO_IMAGES_ENABLED=true` and `pypdfium2`; it renders private
  PDF pages at 2× to a verified PNG or PNG ZIP, not a browser/provider
  fallback. PDF text → Word separately requires
  `WEBAPP_PDF_TO_WORD_ENABLED=true` and `python-docx`; it exports only real
  selectable text, not OCR or visual layout. PDF OCR is a separate local-only
  opt-in: `WEBAPP_DOCUMENT_OCR_PDF_ENABLED=true` requires pypdf, PDFium,
  Pillow and Tesseract and produces a verified private TXT only when every
  bounded PDF page has real text; it does not use a browser, Bot or provider
  fallback. See
  [`PDF_SPLIT_CONTRACT.md`](docs/migration/PDF_SPLIT_CONTRACT.md),
  [`PDF_MERGE_CONTRACT.md`](docs/migration/PDF_MERGE_CONTRACT.md) and
  [`PDF_OPTIMIZE_CONTRACT.md`](docs/migration/PDF_OPTIMIZE_CONTRACT.md),
  [`IMAGE_TO_PDF_CONTRACT.md`](docs/migration/IMAGE_TO_PDF_CONTRACT.md),
  [`PDF_TO_IMAGES_CONTRACT.md`](docs/migration/PDF_TO_IMAGES_CONTRACT.md), and
  [`PDF_TO_WORD_CONTRACT.md`](docs/migration/PDF_TO_WORD_CONTRACT.md), and
  [`PDF_OCR_CONTRACT.md`](docs/migration/PDF_OCR_CONTRACT.md).
- `WEBAPP_IMAGE_OPERATIONS_ENABLED` defaults to `false`. Resize & Aspect
  Studio additionally needs `WEBAPP_IMAGE_RESIZE_ENABLED=true`, Asset Vault,
  Pillow and its own separate persistent
  `WEBAPP_IMAGE_OPERATIONS_ROOT` (for example
  `/data/toanaas_webapp_image_operations`). The root must not overlap Asset
  Vault, Project Package, Document Operations or `/static`. The feature emits
  only verified private PNG artifacts from crop/pad/blur processing; it is not
  AI upscale, a Bot job, provider request or payment path. See
  [`IMAGE_RESIZE_ASPECT_CONTRACT.md`](docs/migration/IMAGE_RESIZE_ASPECT_CONTRACT.md).
- `WEBAPP_IMAGE_ENHANCE_ENABLED` defaults to `false`. Image Enhance Studio
  needs Asset Vault, `WEBAPP_IMAGE_OPERATIONS_ENABLED=true`, Pillow and the
  same separate persistent `WEBAPP_IMAGE_OPERATIONS_ROOT`; it does not enable
  Resize Studio. It creates only verified private PNG artifacts from bounded
  local colour/detail adjustments (and optional deterministic basic upscale),
  never AI edit/upscale, a Bot job, provider request or payment path. See
  [`IMAGE_ENHANCE_CONTRACT.md`](docs/migration/IMAGE_ENHANCE_CONTRACT.md).
- `WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED` defaults to `false`. Brand Overlay
  Studio creates a new verified private PNG from an Asset Vault source plus
  optional owner-scoped logo and/or bounded text; it does not enable browser
  canvas, Bot jobs, provider calls, Xu or payment logic. It shares the
  isolated Image Operations root and may use
  `WEBAPP_IMAGE_BRAND_OVERLAY_FONT_PATH` to pin a server Unicode font for
  text. See
  [`IMAGE_BRAND_OVERLAY_CONTRACT.md`](docs/migration/IMAGE_BRAND_OVERLAY_CONTRACT.md).
- `WEBAPP_STORYBOARD_GRID_ENABLED` defaults to `false`. Storyboard Grid
  Splitter accepts one verified private Asset Vault image and deterministically
  writes a verified JPEG-scene ZIP plus manifest using the isolated Image
  Operations storage boundary. It does not enable AI, Bot jobs, provider
  calls, Xu, PayOS or browser rendering. See
  [`STORYBOARD_GRID_SPLITTER_CONTRACT.md`](docs/migration/STORYBOARD_GRID_SPLITTER_CONTRACT.md).
- `WEBAPP_MEMORY_CENTER_ENABLED` defaults to `true`. `/notes` and
  `/reminders` are a signed-account, Web-owned workspace for private notes,
  version history and view-only reminders. It does not read or mutate Bot
  memory, Telegram, wallet/Xu, PayOS, provider or job state. For durable
  production history, the Web-owned session database must use the same
  persistent-volume contract described above; do not advertise notification
  delivery unless a separate, audited adapter is enabled. See
  [`MEMORY_CENTER_CONTRACT.md`](docs/migration/MEMORY_CENTER_CONTRACT.md).
- `WEBAPP_DATA_CONTROLS_ENABLED` defaults to `false`. `/account/data-controls`
  is an opt-in Web-only privacy control: it can download a bounded direct JSON
  copy of Web-authored profile, Memory, Prompt Library and Workboard data, and
  submit/cancel a staged `web_authoring_only` erasure review request. It never
  automatically deletes data and never reads, mutates or promises action for
  Telegram/Bot, Xu/PayOS, provider, job, asset, credential, raw-audit or
  support/operations data. See
  [`DATA_CONTROLS_CONTRACT.md`](docs/migration/DATA_CONTROLS_CONTRACT.md).
- `WEBAPP_ANALYTICS_WORKSPACE_ENABLED` defaults to `true`. `/analytics` is a
  signed-account workspace for reports, metric definitions, manual snapshots
  and human-authored findings. It calculates only from numbers the account
  saved with server-side `Decimal`; it never connects a social platform,
  reads Bot/provider reports, creates AI insight, handles revenue/Xu/PayOS,
  starts jobs, publishes or creates a stored report file.
  `WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED` separately defaults to `false`:
  enable it only after reviewing the narrow, owner-scoped finalized-report CSV
  attachment contract. That attachment is generated from active Web-owned
  manual records on demand with session, CSRF and revision checks; it is not a
  Bot `/campaign/report`, platform report, stored asset, job or delivery
  artifact. See
  [`ANALYTICS_WORKSPACE_CONTRACT.md`](docs/migration/ANALYTICS_WORKSPACE_CONTRACT.md).
- `WEBAPP_GROWTH_REVIEW_ENABLED` defaults to `true`. `/growth/ai` is a signed,
  request-only **Growth Review** that mirrors the Bot's deterministic score
  and recommendation thresholds over six values the account manually enters.
  It is not Growth AI: it never connects to a platform, reads canonical
  revenue, calls Bot/provider/model, changes Xu/PayOS, creates a job or saves
  the input/result. See
  [`GROWTH_REVIEW_CONTRACT.md`](docs/migration/GROWTH_REVIEW_CONTRACT.md).
- `WEBAPP_WORKBOARD_ENABLED` defaults to `true`. `/workboard` is a
  signed-account Kanban and self-review queue for metadata the same Web
  account owns. It can reference verified Web Project, Campaign, Analytics,
  Note or Draft records, but never creates a Bot job, publish action,
  notification, provider request, wallet/Xu mutation or PayOS operation. See
  [`WORKBOARD_REVIEW_QUEUE_CONTRACT.md`](docs/migration/WORKBOARD_REVIEW_QUEUE_CONTRACT.md).
- `WEBAPP_VOICE_STUDIO_ENABLED` defaults to `true`. `/voice-studio` is a
  signed-account authoring workspace for voice direction, consent metadata,
  scripts, local cue-sheet estimates and revision history. It never stores
  audio/provider IDs, invokes TTS or clone, creates an audio preview/output,
  changes Xu/PayOS, or mutates Bot state. See
  [`VOICE_STUDIO_CONTRACT.md`](docs/migration/VOICE_STUDIO_CONTRACT.md).
- `WEBAPP_VIDEO_STUDIO_ENABLED` defaults to `true`. `/video-studio` is a
  signed-account workspace for video brief, scenes, runtime estimate,
  self-review and revision history. It never uploads/render media, calls a
  provider/Bot engine, creates preview/output, changes Xu/PayOS or mutates
  canonical jobs. See
  [`VIDEO_PRODUCTION_STUDIO_CONTRACT.md`](docs/migration/VIDEO_PRODUCTION_STUDIO_CONTRACT.md).
- `WEBAPP_SUPPORT_DESK_ENABLED` defaults to `true`. `/support` and
  `/tickets` are a signed-account, Web-owned Support Desk for text-only case
  intake and timeline. `/admin/support` is separately protected by a
  server-side `role_cache` (`admin`, `support_manager` or
  `support_operator`), never an email list or browser role. It does not read
  Bot tickets, send notifications, accept payment proof, alter Xu/PayOS,
  call providers, refund or create jobs. See
  [`WEB_SUPPORT_DESK_CONTRACT.md`](docs/migration/WEB_SUPPORT_DESK_CONTRACT.md).
- `WEBAPP_AUTOPILOT_ENABLED` defaults to `false`. `/operations` and the
  staff-only `/admin/operations` can observe Web-native Support Desk metadata
  and a signed scheduler's bounded receipts. Automatic metadata triage is
  separately opt-in and remains unable to call the Bot/provider, mutate
  Xu/PayOS, send a customer message, retry a job or change deployment/code.
  Enable it only through the one-replica, HMAC-protected runbook in
  [`OPERATIONS_AUTOPILOT_CONTRACT.md`](docs/migration/OPERATIONS_AUTOPILOT_CONTRACT.md).
- `WEBAPP_RELIABILITY_FOLLOWUP_ENABLED` defaults to `false`. The staff-only
  `/admin/reliability` queue can aggregate only allow-listed Web-native 5xx
  metadata and existing Support triage; it is not a raw log, auto-fix,
  Railway restart/deploy, Bot/provider/job/payment/wallet executor or
  customer-contact channel. It requires the Autopilot contract and its
  Web-only incident secret; use the bounded retention and enablement rules in
  [`WEB_RELIABILITY_FOLLOWUP_CONTRACT.md`](docs/migration/WEB_RELIABILITY_FOLLOWUP_CONTRACT.md).
- `WEBAPP_NOTIFICATION_CENTER_ENABLED` defaults to `true`, while
  `WEBAPP_NOTIFICATION_AUTOMATION_ENABLED` defaults to `false`. `/inbox` and
  `/automation` are durable, signed-account **in-app records only**; phase 1
  can materialize an overdue Web reminder but never sends Telegram/email/SMS/
  web push, calls Bot/provider, or changes wallet/Xu, PayOS, jobs, deployment
  or a customer reply. Enable its separate HMAC scheduler only after the Web
  SQLite database is verified on a persistent volume with one replica. In a
  production-like environment, a valid explicit replica attestation '=1' is
  also required; invalid budgets or deployment guards return a nonce-consuming
  guarded receipt rather than running a partial tick. Customer summaries show
  only owner-scoped materialization metadata, never global scheduler receipts;
  see
  [`WEB_NOTIFICATION_AUTOMATION_CONTRACT.md`](docs/migration/WEB_NOTIFICATION_AUTOMATION_CONTRACT.md).

## Authority boundary

The Telegram Bot is the sole authority for Telegram identity, Xu ledger,
PayOS orders/webhook, provider execution, jobs and output delivery. The Web
App owns signed sessions, CSRF, presentation metadata and typed calls to the
private Bot bridge.

- No browser-supplied Telegram ID, wallet ID, `admin_id`, provider state or
  PayOS value is trusted.
- Telegram Login can establish a signed Web session through Telegram OIDC when
  BotFather Web Login is configured. Bot-owned Xu/jobs/assets still require
  the one-time signed Bot link, and an OIDC-created account must prove the
  same Telegram identity before those canonical data surfaces unlock.
- The callback adapter is an explicitly separate Bot bridge deployment; it is
  not implied by this Web-only branch or by entering a Telegram ID. The static
  migration preflight records any difference between the frozen Bot baseline
  and the audited bridge worktree before a live link is enabled.
- The Bot one-time link is off by default even when the Web callback receiver
  has credentials. Set the non-secret release gate
  `WEBAPP_TELEGRAM_BOT_LINK_ENABLED=true` only after the matching Bot adapter
  has been deployed and configured; a valid signed callback is still the
  only end-to-end proof.
- The Web App does not mount a PayOS webhook, direct payment signer, wallet
  writer or manual-top-up inbox.
- A canonical Bot checkout URL may be shown only after strict HTTPS/PayOS-host
  validation; it is never persisted by the Web App.
- Manual reconciliation remains in Bot via `/thucong`; the Portal can only
  open that handoff and refresh canonical wallet history.
- `/campaigns` is a Web-owned personal planning board with account ownership,
  CSRF, idempotency and audit. Its calendar/self-review states never publish,
  create a Bot campaign, calculate analytics/revenue, call a provider or
  affect Xu/PayOS; see
  [`CAMPAIGN_PLANNER_BOUNDARY.md`](docs/migration/CAMPAIGN_PLANNER_BOUNDARY.md).
- `/asset-vault` is a separate Web-owned private file library. It is not a
  Bot output library, provider staging area, wallet/PayOS surface, or proof
  that an engine generated an artifact. See
  [`ASSET_VAULT_CONTRACT.md`](docs/migration/ASSET_VAULT_CONTRACT.md).
- `/notes` and `/reminders` are a separate Web-owned Memory Center. They use
  the signed Web account, CSRF, owner checks, idempotency and audit, but do
  not mirror Bot `memory_*` tables or claim that Telegram/email/push has been
  delivered. Bot memory AI classification, storage quota/add-ons and its
  actual reminder sender remain outside this Web-only contract.
- `/inbox` and `/automation` are a separate Web-native Inbox Center. A
  durable record means only that the signed Web account can view it on return;
  it is not Telegram/email/SMS/web-push delivery. Its current scheduler may
  materialize only an overdue Web Memory reminder without changing that source;
  it does not auto-schedule Workboard/Campaign local-time fields, contact a
  customer, mutate Bot/provider/PayOS/wallet/job state or deploy. See
  [`WEB_NOTIFICATION_AUTOMATION_CONTRACT.md`](docs/migration/WEB_NOTIFICATION_AUTOMATION_CONTRACT.md).
- `/workboard` is a separate Web-owned Workboard & Review Queue. Its states
  and checklists are private self-management metadata; `review` and `done`
  are never a Bot/admin approval, job completion, publication, notification
  or external automation claim. It accepts only owner-verified opaque
  references and cannot fetch a URL, upload a file or invoke any external
  system. See
  [`WORKBOARD_REVIEW_QUEUE_CONTRACT.md`](docs/migration/WORKBOARD_REVIEW_QUEUE_CONTRACT.md).
- `/support` and `/tickets` are a separate Web-owned Support Desk. Cases,
  public replies and staff-only notes are bound to the signed Web account and
  server-side Support role. They never mirror Bot ticket state, create a
  Telegram/email/push delivery, accept manual payment evidence, alter the
  wallet/Xu/PayOS ledger, execute a refund or call a provider/job. See
  [`WEB_SUPPORT_DESK_CONTRACT.md`](docs/migration/WEB_SUPPORT_DESK_CONTRACT.md).
- `/project-packages` is a distinct Web-native private ZIP export of a
  Project snapshot. It does not create a Bot job, copy Asset Vault source
  blobs, change Xu, invoke PayOS or call a provider. See
  [`PROJECT_PACKAGE_CONTRACT.md`](docs/migration/PROJECT_PACKAGE_CONTRACT.md).
- `/documents/split`, `/documents/merge`, `/documents/compress`,
  `/documents/image-to-pdf`, `/documents/pdf-to-images` and
  `/documents/pdf-to-word` are distinct
  Web-native document operations:
  the PDF tools accept only verified private Asset Vault PDFs, while Image to
  PDF accepts ordered, verified private JPEG/PNG/WebP assets. Each writes a
  separately validated private attachment and does not create a Bot job, call
  a provider, alter Xu or touch PayOS. PDF Optimize only delivers when its
  final artifact is meaningfully smaller; PDF → images delivers a verified
  PNG or deterministic PNG ZIP; PDF text → Word delivers only when
  the private source contains real extractable text and its fresh DOCX passes
  verification. See
  [`PDF_SPLIT_CONTRACT.md`](docs/migration/PDF_SPLIT_CONTRACT.md),
  [`PDF_MERGE_CONTRACT.md`](docs/migration/PDF_MERGE_CONTRACT.md) and
  [`PDF_OPTIMIZE_CONTRACT.md`](docs/migration/PDF_OPTIMIZE_CONTRACT.md),
  [`IMAGE_TO_PDF_CONTRACT.md`](docs/migration/IMAGE_TO_PDF_CONTRACT.md),
  [`PDF_TO_IMAGES_CONTRACT.md`](docs/migration/PDF_TO_IMAGES_CONTRACT.md), and
  [`PDF_TO_WORD_CONTRACT.md`](docs/migration/PDF_TO_WORD_CONTRACT.md).

See [the current migration contracts](docs/migration/README.md), especially
`PAYOS_WALLET_JOB_MAP.md`, `FEATURE_CONFIRM_CONTRACT.md`, and
`TELEGRAM_WEB_CONNECTION.md`. Historical files under `docs/webapp/` describe
the retired prototype and are not runtime architecture.
