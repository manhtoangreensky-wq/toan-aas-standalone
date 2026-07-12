# TOAN AAS Web App Production Architecture

Date: 2026-07-11 (superseded prototype notes corrected)

## Scope

This repository is the standalone web app for `app.toanaas.vn`.

The Telegram bot remains the canonical production authority for identity,
wallet/Xu, PayOS, jobs, providers and delivery. This Web App provides a clean,
clear customer workflow using signed sessions and a private bridge; it does
not reproduce those writers locally.

## Core Flow

TOAN AAS follows the simplified automation process:

`Intent -> Suggestion/Plan -> Prompt/Configuration -> Pricing -> Confirm -> Job -> Provider/Worker -> Result -> Save/Audit`

Rules:

- No paid action without final confirmation.
- No provider call from raw UI buttons.
- No fake output if a provider or worker is not ready.
- Long-running tasks must become jobs with status.
- Customer-facing errors must be soft and actionable.
- Internal details, API keys, and raw provider responses are not shown to users.

## Layered Gate Model

1. UI gate: keep screens simple and show the next logical action only.
2. Auth gate: admin actions require server-side `ADMIN_IDS` / `ADMIN_ID`.
3. Billing gate: only the canonical Bot creates a PayOS order and verifies its
   webhook; Web can proxy a reviewed request but never signs/finalizes it.
4. Capability gate: provider, worker, and feature flags decide whether a job can run.
5. Job gate: job state prevents duplicate or unsafe execution.
6. Provider gate: service modules submit jobs to tested providers only.
7. Persistence/audit gate: Bot persists wallet/payment/job authority; Web
   stores only sessions, CSRF, audit metadata and short-lived safe receipts.

## Current Production Entrypoint

- Railway start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Primary app file: `app.py`
- Legacy files such as `main.py` are not the Railway production entrypoint.

## Key Routes

- `/` - customer workspace
- `/login` - Email/OAuth or one-time Bot-verified Telegram sign-in
- `/admin-app` - admin control panel
- `/health` - runtime health
- `/api/v1/health` - API health
- `/api/v1/payments/create` - guarded signed proxy to a reviewed Bot payment adapter
- `/api/v1/payments/{id}` - owner-scoped canonical payment read

There is no Web-owned PayOS webhook or direct billing route in the current
runtime. See `docs/migration/PAYOS_WALLET_JOB_MAP.md` for the active contract.

## Automation Goal

The goal is not just menus. The web app should help users move from need to outcome:

- plan content
- create prompts
- confirm paid work
- track jobs
- store results
- reuse assets
- connect back to Telegram only where helpful

The web app should stay clean and clear, especially for non-technical customers.
