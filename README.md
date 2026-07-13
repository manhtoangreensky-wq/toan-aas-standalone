# TOAN AAS Standalone Web App

Production Web App for `app.toanaas.vn`.

## Runtime

- Railway entrypoint: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Compatibility entrypoint: `main:app` exports the exact same application.
- Health checks: `/health`, `/api/v1/health`
- Customer portal: `/dashboard`, `/projects`, `/project-packages`, `/asset-vault`, `/notes`, `/reminders`, `/wallet`, `/jobs`, `/assets`
- Admin Portal: `/admin` (signed session plus current canonical Bot role)

## Required Railway production configuration

- `WEB_SESSION_SECRET` is required: generate one long random value in the
  Railway **Variables** page. It signs Web sessions and must never be placed
  in Git, browser JavaScript, tickets or logs. The app intentionally refuses
  to start without it in production instead of issuing forgeable sessions.
- Persist the Web-owned session database on the service's Railway volume with
  an absolute `WEBAPP_SESSION_DB_PATH`, an existing
  `RAILWAY_VOLUME_MOUNT_PATH`, or the standard persistent `/data` mount. See
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
  selectable text, not OCR or visual layout. See
  [`PDF_SPLIT_CONTRACT.md`](docs/migration/PDF_SPLIT_CONTRACT.md),
  [`PDF_MERGE_CONTRACT.md`](docs/migration/PDF_MERGE_CONTRACT.md) and
  [`PDF_OPTIMIZE_CONTRACT.md`](docs/migration/PDF_OPTIMIZE_CONTRACT.md),
  [`IMAGE_TO_PDF_CONTRACT.md`](docs/migration/IMAGE_TO_PDF_CONTRACT.md),
  [`PDF_TO_IMAGES_CONTRACT.md`](docs/migration/PDF_TO_IMAGES_CONTRACT.md), and
  [`PDF_TO_WORD_CONTRACT.md`](docs/migration/PDF_TO_WORD_CONTRACT.md).
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
- `WEBAPP_MEMORY_CENTER_ENABLED` defaults to `true`. `/notes` and
  `/reminders` are a signed-account, Web-owned workspace for private notes,
  version history and view-only reminders. It does not read or mutate Bot
  memory, Telegram, wallet/Xu, PayOS, provider or job state. For durable
  production history, the Web-owned session database must use the same
  persistent-volume contract described above; do not advertise notification
  delivery unless a separate, audited adapter is enabled. See
  [`MEMORY_CENTER_CONTRACT.md`](docs/migration/MEMORY_CENTER_CONTRACT.md).
- `WEBAPP_SUPPORT_DESK_ENABLED` defaults to `true`. `/support` and
  `/tickets` are a signed-account, Web-owned Support Desk for text-only case
  intake and timeline. `/admin/support` is separately protected by a
  server-side `role_cache` (`admin`, `support_manager` or
  `support_operator`), never an email list or browser role. It does not read
  Bot tickets, send notifications, accept payment proof, alter Xu/PayOS,
  call providers, refund or create jobs. See
  [`WEB_SUPPORT_DESK_CONTRACT.md`](docs/migration/WEB_SUPPORT_DESK_CONTRACT.md).

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
