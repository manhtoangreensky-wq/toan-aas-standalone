# TOAN AAS Web App Production Architecture

Date: 2026-06-16

## Scope

This repository is the standalone web app for `app.toanaas.vn`.

The Telegram bot remains a separate production channel. This web app should not copy every bot screen 1:1. It should provide a clean, clear, easy customer workflow and act as the TOAN AAS Control Center.

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
3. Billing gate: paid actions create an order through billing service only.
4. Capability gate: provider, worker, and feature flags decide whether a job can run.
5. Job gate: job state prevents duplicate or unsafe execution.
6. Provider gate: service modules submit jobs to tested providers only.
7. Persistence/audit gate: wallet, payment, entitlement, job, and admin events are stored.

## Current Production Entrypoint

- Railway start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Primary app file: `app.py`
- Legacy files such as `main.py` are not the Railway production entrypoint.

## Key Routes

- `/` - customer workspace
- `/login` - Telegram ID login bridge
- `/admin-app` - admin control panel
- `/health` - runtime health
- `/api/v1/health` - API health
- `/api/v1/billing/create-payment-link` - single source for PayOS payment link creation
- `/api/v1/billing/webhook/payos` - single PayOS webhook receiver

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
