# TOAN AAS Standalone Web App

Production Web App for `app.toanaas.vn`.

## Runtime

- Railway entrypoint: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Compatibility entrypoint: `main:app` exports the exact same application.
- Health checks: `/health`, `/api/v1/health`
- Customer portal: `/dashboard`, `/projects`, `/asset-vault`, `/wallet`, `/jobs`, `/assets`
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

See [the current migration contracts](docs/migration/README.md), especially
`PAYOS_WALLET_JOB_MAP.md`, `FEATURE_CONFIRM_CONTRACT.md`, and
`TELEGRAM_WEB_CONNECTION.md`. Historical files under `docs/webapp/` describe
the retired prototype and are not runtime architecture.
