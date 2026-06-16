# TOAN AAS Web App Production Promotion Report

Date: 2026-06-16

## Objective

Prepare `app.toanaas.vn` as the main TOAN AAS Control Center without changing the Telegram bot production files.

## Done

- Confirmed Railway production entrypoint uses `app.py`.
- Added `/health` and `/api/v1/health`.
- Mounted `/static` assets when the static folder exists.
- Restricted CORS default origins to `app.toanaas.vn` and `toanaas.vn`.
- Added server-side admin identity helper.
- Removed automatic admin promotion from username `admin`.
- Removed public default legacy `ADMIN_PASSWORD`.
- Guarded admin dashboard/user/Xu APIs.
- Guarded manual top-up admin list/approve APIs.
- Added ERP admin API header guard.
- Converted customer PayOS UI to `/api/v1/billing/create-payment-link`.
- Kept customer PayOS compatibility wrapper as a billing-source wrapper only.
- Added storage add-on PayOS flow with 50MB free and paid monthly blocks.
- Added admin storage grant endpoint and admin UI form.
- Guarded placeholder web AI tools behind `WEB_TOOL_PROCESS_ENABLED=false` default.
- Fixed campaign page to use logged-in `user_id` instead of `admin_web`.
- Added docs for architecture, security, DB schema, and PayOS single source.

## Not Touched

- `D:\TOANAAS\bot telegram\bot.py`
- Telegram bot index files
- Telegram bot PayOS webhook
- Telegram bot top-up logic
- Telegram bot wallet/Xu balance logic
- Telegram bot public image/video flows

## Follow-up

- Add real signed web sessions instead of localStorage-only UX hints.
- Add admin audit event table for all admin writes.
- Connect provider/job services only after smoke tests pass.
- Keep every future paid feature on the gate chain:
  `pricing -> confirm -> job -> provider/worker -> result -> audit`.
