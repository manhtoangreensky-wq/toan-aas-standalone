# TOAN AAS Standalone Web App

Production Web App for `app.toanaas.vn`.

## Runtime

- Railway entrypoint: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Compatibility entrypoint: `main:app` exports the exact same application.
- Health checks: `/health`, `/api/v1/health`
- Customer portal: `/dashboard`, `/projects`, `/project-packages`, `/asset-vault`, `/wallet`, `/jobs`, `/assets`
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
  Merge, PDF Optimize and Image to PDF require
  Asset Vault **and** a separate persistent
  `WEBAPP_DOCUMENT_OPERATIONS_ROOT` (for example
  `/data/toanaas_webapp_document_operations`). It may not overlap Asset Vault,
  Project Package or `/static`; startup fails closed when the parser/runtime
  or private storage boundary is absent. Image to PDF also requires the
  separate opt-in `WEBAPP_IMAGE_TO_PDF_ENABLED=true` gate and its Pillow
  decoder runtime. See
  [`PDF_SPLIT_CONTRACT.md`](docs/migration/PDF_SPLIT_CONTRACT.md),
  [`PDF_MERGE_CONTRACT.md`](docs/migration/PDF_MERGE_CONTRACT.md) and
  [`PDF_OPTIMIZE_CONTRACT.md`](docs/migration/PDF_OPTIMIZE_CONTRACT.md), and
  [`IMAGE_TO_PDF_CONTRACT.md`](docs/migration/IMAGE_TO_PDF_CONTRACT.md).

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
- `/project-packages` is a distinct Web-native private ZIP export of a
  Project snapshot. It does not create a Bot job, copy Asset Vault source
  blobs, change Xu, invoke PayOS or call a provider. See
  [`PROJECT_PACKAGE_CONTRACT.md`](docs/migration/PROJECT_PACKAGE_CONTRACT.md).
- `/documents/split`, `/documents/merge`, `/documents/compress` and
  `/documents/image-to-pdf` are distinct Web-native document operations:
  the PDF tools accept only verified private Asset Vault PDFs, while Image to
  PDF accepts ordered, verified private JPEG/PNG/WebP assets. Each writes a
  separately validated private attachment and does not create a Bot job, call
  a provider, alter Xu or touch PayOS. PDF Optimize only delivers when its
  final artifact is meaningfully smaller. See
  [`PDF_SPLIT_CONTRACT.md`](docs/migration/PDF_SPLIT_CONTRACT.md),
  [`PDF_MERGE_CONTRACT.md`](docs/migration/PDF_MERGE_CONTRACT.md) and
  [`PDF_OPTIMIZE_CONTRACT.md`](docs/migration/PDF_OPTIMIZE_CONTRACT.md), and
  [`IMAGE_TO_PDF_CONTRACT.md`](docs/migration/IMAGE_TO_PDF_CONTRACT.md).

See [the current migration contracts](docs/migration/README.md), especially
`PAYOS_WALLET_JOB_MAP.md`, `FEATURE_CONFIRM_CONTRACT.md`, and
`TELEGRAM_WEB_CONNECTION.md`. Historical files under `docs/webapp/` describe
the retired prototype and are not runtime architecture.
