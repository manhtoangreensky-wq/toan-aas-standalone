# TOAN AAS Control Center

Production web app for `app.toanaas.vn`.

## Runtime

- Railway entrypoint: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Health checks:
  - `/health`
  - `/api/v1/health`
- Control gate status:
  - `/api/v1/control/status` (admin-only, no secrets)
- Customer app: `/`
- Admin app: `/admin-app`

## Operating Principles

The web app is not a 1:1 copy of the Telegram bot. It is the clean TOAN AAS Control Center:

1. Customer chooses an intent.
2. Web app guides them through suggestions/planning.
3. Paid actions show pricing before confirmation.
4. Billing creates an order through one PayOS source.
5. Provider/worker jobs run only after gates pass.
6. Results, entitlements, usage, and audit events are persisted.

## Production Guards

- Admin role is server-side through `ADMIN_IDS` / `ADMIN_ID`.
- Username `admin` does not automatically become admin.
- PayOS creation source: `/api/v1/billing/create-payment-link`.
- PayOS webhook source: `/api/v1/billing/webhook/payos`.
- Admin dashboard reads `/api/v1/control/status` for DB volume, PayOS, storage and feature-gate readiness.
- Placeholder web tools do not deduct Xu unless `WEB_TOOL_PROCESS_ENABLED=true`.
- Static assets are served from `/static`.

See `docs/webapp/` for the production architecture, security audit, DB schema audit, and PayOS single-source notes.
