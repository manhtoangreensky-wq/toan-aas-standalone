# TOAN AAS Web App Security Audit

Date: 2026-06-16

## Admin Auth

Previous risk:

- The web app could treat username `admin` as admin.
- Some admin screens relied on `localStorage.role`.
- Legacy `ADMIN_PASSWORD` had a public default value.

Current guard:

- Admin identity is derived server-side from `ADMIN_IDS`, `ADMIN_ID`, `OWNER_TELEGRAM_ID`, or `ADMIN_TELEGRAM_IDS`.
- Register/login no longer promotes username `admin` automatically.
- Legacy password auth no longer has a default password. If `ADMIN_PASSWORD` is missing, `/verify` returns unavailable.
- Manual top-up admin APIs require `admin_id`.
- ERP admin APIs require `X-TOAN-AAS-User-Id` or `admin_id` and validate it server-side.

## Frontend Role

`localStorage.role` is only a UI hint. It is not considered authorization.

Server-side admin checks must protect any write or sensitive read endpoint.

## CORS

Default allowed origin:

- `https://app.toanaas.vn`

The root/marketing origin is not credentialed by default. Add it through
`CORS_ALLOW_ORIGINS` only after it is operated and audited as the same trust
boundary as the signed Web App.

Override with `CORS_ALLOW_ORIGINS`.

## Secret Handling

Do not log:

- PayOS API key
- PayOS checksum key
- provider keys
- admin tokens
- raw payment signatures

## Remaining Follow-up

- Replace legacy cookie-only `/verify` with a signed server session if the admin password flow is kept.
- Add request audit logs for all admin write actions.
- Add rate limiting for login and payment creation.
- Move every placeholder tool to a feature flag before public release.
