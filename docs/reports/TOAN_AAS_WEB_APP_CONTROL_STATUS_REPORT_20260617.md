# TOAN AAS Web App Control Status Report - 2026-06-17

## Scope

Added a guarded control-center status endpoint and admin dashboard card for the standalone web app.

## What Changed

- Added `/api/v1/control/status`.
- Added admin dashboard "System Gate" card.
- Reported DB path, DB persistence risk, table counts, PayOS bridge readiness, storage policy, and provider feature flag.
- Connected customer workflow "Save plan" to the web app media asset API with browser-local fallback.
- Added optional `user_id` ownership metadata to `media_assets` without breaking old rows.
- Kept PayOS as a single source through `/api/v1/billing/create-payment-link` and `/api/v1/billing/webhook/payos`.
- Kept provider jobs guarded unless feature flags/smoke tests are explicitly enabled.

## Storage Policy

- Base free storage: 50MB.
- Add-on block: 10,000 VND per +50MB/month.
- Fixed packages: 10k/50MB, 20k/100MB, 50k/250MB, 100k/500MB.
- Custom package: every additional 10k adds +50MB/month.

## Safety

- No API keys, tokens, payment secrets, or raw webhook signatures are exposed.
- Admin endpoint requires server-side admin ID validation.
- Telegram bot files were not touched.

## Checks

- `python -m py_compile`: PASS.
- `git diff --check`: PASS.
- Local import smoke with bundled Codex Python: blocked because bundled runtime is missing `pydantic_settings`; Railway requirements include `pydantic-settings==2.1.0`.
