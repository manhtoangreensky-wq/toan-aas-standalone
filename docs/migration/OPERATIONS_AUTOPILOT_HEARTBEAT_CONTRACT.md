# Operations Autopilot — Missed-Cron Heartbeat Follow-up Contract

## Purpose

This optional Web-only playbook records a local Operations incident when a
newly authenticated Railway Cron tick arrives later than its explicit expected
interval. It is an observability follow-up for staff; it is **not** a Cron
repair, Railway monitor, deployment tool, notification sender or external
executor.

It never imports or calls the Telegram Bot, Core Bridge, provider, Xu/wallet,
PayOS, job, asset delivery, deployment, messaging or notification systems. It
does not restart, reschedule, retry or otherwise self-heal Cron.

## Enablement and configuration

All of these conditions are required before the playbook can write metadata:

| Variable | Default | Constraint |
| --- | --- | --- |
| `WEBAPP_AUTOPILOT_ENABLED` | `false` | Existing signed Operations scheduler flag. |
| `WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED` | `false` | Existing allow-list for local metadata actions only. |
| `WEBAPP_AUTOPILOT_HEARTBEAT_FOLLOWUP_ENABLED` | `false` | Separately enables this heartbeat follow-up. |
| `WEBAPP_AUTOPILOT_HEARTBEAT_EXPECTED_SECONDS` | unset | Required when the heartbeat flag is enabled; integer from 300 through 86,400. |
| `WEBAPP_AUTOPILOT_HEARTBEAT_GRACE_SECONDS` | `120` | Integer from 0 through 3,600. |

The expected interval is never guessed from a Railway schedule. If the
separately enabled heartbeat has malformed or missing configuration, the
normal signed tick is recorded as a `guarded` receipt with
`OPS_HEARTBEAT_CONFIG_UNVERIFIED`; no heartbeat incident is created. Existing
single-replica, persistent-store, HMAC, nonce, deadline and lease guards still
apply unchanged.

## Detection semantics

```text
current authenticated tick acquires live Operations lease
    -> read only the persisted `railway_cron` baseline for this configuration
       fingerprint and current Web-process epoch
    -> if no matching armed baseline exists, record no finding
    -> otherwise confirm its referenced run is an already *completed*
       `railway_cron` run (never the newly-created current `started` run)
    -> compare current server time with explicit interval + grace
    -> if late, write one local Operations incident/observation
    -> after a successfully completed tick only, advance the persisted baseline
```

`web_ops_heartbeat_baselines` is an additive, Web-owned local table keyed by
scope. Its row binds the policy/configuration fingerprint, a fresh
Web-process epoch, and an exact completed run id. The first valid tick after
feature enablement, a configuration change, or a process redeploy is reported
as `baseline_pending` and never manufactures a late-Cron finding — even when
the database contains older completed Cron rows. Invalid/future baseline
history is guarded (`OPS_HEARTBEAT_HISTORY_INVALID`) rather than interpreted
as lateness.

The tick checks its exact fence before the local write. A concurrent request
that sees an active lease returns the existing guarded lease receipt and never
runs this playbook. The per-gap observation uses a server-secret HMAC marker,
so a stale retry cannot append repeated observations for the same completed
predecessor.

## Local data boundary

Only these standalone-Web tables may change:

- `web_ops_heartbeat_baselines`: configuration/process-bound local arming
  state, advanced only when the same live-fenced scheduler run is completed;
- `web_ops_incidents`: one `scheduler_heartbeat_late` / `scheduler` metadata
  incident with no account, Support case, customer narrative, provider handle
  or payment data;
- `web_ops_incident_observations`: a compact HMAC-derived late-gap receipt;
- `web_ops_run_steps` and `web_ops_playbook_runs`: bounded audit metadata for
  the accepted scheduler run.

There is no automatic close or repair. A subsequent on-time tick does not
claim the Cron, service, provider or customer work was fixed. Staff retain the
normal Operations review and audit process.

Customer `GET /api/v1/operations/status` contains no global scheduler-health
diagnostics; it remains scoped to the requesting Web account. Heartbeat
diagnostics (`disabled`, `baseline_pending`, `within_window`, `late`, or
`guarded`) and the count of open local follow-ups are available only in the
staff-protected `GET /api/v1/operations/admin/summary` read model. Neither
read route creates metadata, starts a worker, or sends a message.

## Staff portal projection

`/admin/operations` projects the existing heartbeat summary as a compact,
read-only Scheduler heartbeat card. The browser accepts only the five fixed
states above, the two reviewed guard codes
`OPS_HEARTBEAT_CONFIG_UNVERIFIED` / `OPS_HEARTBEAT_HISTORY_INVALID`, a boolean
previous-tick signal and a bounded count of open follow-ups. Any malformed or
extended heartbeat object fails closed with the rest of the staff summary;
neither the raw scheduler summary nor run/baseline IDs enter Portal state.

The card describes only whether a signed tick reached this Web App within the
configured window or needs staff review. `late` may link to the protected
Reliability follow-up screen and show the already-redacted local count; it
never claims Railway, a provider, Bot, job or deployment is healthy. It has no
repair/restart/retry/cron-control button and does not expose a timestamp,
configuration fingerprint, lease, nonce, HMAC, run ID or customer data.

## Required focused verification

1. The first valid tick makes no heartbeat incident even with historical
   completed scheduler rows already present; it persists a fresh baseline.
2. A redeploy or heartbeat configuration change re-arms a baseline before it
   can assess a gap.
3. A late gap after that matching completed baseline creates exactly one local
   `scheduler_heartbeat_late` incident and no Support, payment, job or
   external side effect.
4. A stale/replayed baseline cannot append a duplicate late observation.
5. A guarded concurrent lease never creates a heartbeat incident.
6. Missing/invalid heartbeat configuration is a guarded, nonce-consuming
   receipt and does not create an incident.
7. Source review confirms no Bot/bridge/provider/wallet/PayOS/job/deploy/
   notification imports or calls were added.
