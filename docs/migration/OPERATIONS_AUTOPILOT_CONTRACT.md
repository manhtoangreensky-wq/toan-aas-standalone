# Operations Autopilot & Complaint Triage Contract

## Purpose

Operations Autopilot makes the standalone Web App observable and safer to run
when no operator is present. It is a **controlled local-operations system**,
not a self-modifying deployment agent or a general-purpose autonomous repair
agent. Every accepted scheduler run is bounded, replay-protected, auditable
and intentionally narrow.

The Bot remains separate. This module must not import Bot code, call a
provider, alter Xu, start/finalize PayOS, issue a refund, mutate canonical Bot
jobs, publish content, deploy/restart Railway, edit code, change secrets, or
send an external notification.

An Operations approval is currently an **audited decision record only**. An
approved record does not execute a payment, wallet, provider, Bot, job,
delivery, deployment or customer-contact action. A separately reviewed,
least-privilege executor would be required for every such action in the
future.

## Runtime shape

```text
Railway Cron invoker (short-lived, at least 5 min)
  -> signed POST /internal/v1/operations/tick
       -> lease + nonce replay check
       -> local database readiness probe
       -> deterministic Support Desk metadata triage
       -> SLA-breach incident upsert and approval proposal records only
       -> bounded recovery reconciliation for ordinary Web-support incidents only
       -> append immutable run, incident and audit records
       -> exit

Signed Web/Admin Portal
  -> /operations and /admin/operations
       -> health, runs, incidents, complaint queue, pending approvals
```

The Cron invoker must be a separate short-lived service. It signs one request
to the Web service and exits; it never opens the Web SQLite file or shares the
Web service volume. The current Web-owned state is SQLite, so production must
run **one Web replica only** while this topology is used. Horizontal Web
scaling is not supported until leases, nonces and idempotency records move to
a shared transactional database such as PostgreSQL.

## Feature flags and secrets

| Variable | Default | Meaning |
| --- | --- | --- |
| `WEBAPP_AUTOPILOT_ENABLED` | `false` | Enables the internal tick and portal read views. |
| `WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED` | `false` | Allows only pre-approved low-risk repair playbooks. |
| `WEBAPP_AUTOPILOT_TICK_SECRET` | unset | Shared Web/Cron HMAC key, at least 32 UTF-8 bytes. Never expose it to browser/client/logs. |
| `WEBAPP_AUTOPILOT_INCIDENT_SECRET` | unset | Web-only HMAC key, at least 32 UTF-8 bytes, for opaque incident/proposal fingerprints. Required only when safe remediation is enabled. Never give it to Cron/browser. |
| `WEBAPP_AUTOPILOT_TICK_KEY_ID` | `primary` | Shared Web/Cron key label matching `^[a-z0-9_-]{1,32}$`. The current implementation supports one active key only; there is no overlapping dual-key rotation. |
| `WEBAPP_AUTOPILOT_TICK_URL` | unset | Cron-only exact HTTPS URL to `/internal/v1/operations/tick`, for example `https://app.toanaas.vn/internal/v1/operations/tick`. |
| `WEBAPP_AUTOPILOT_TICK_ORIGIN` | unset | Cron-only pinned pure HTTPS origin, for example `https://app.toanaas.vn`; no path, query, fragment, userinfo or non-standard HTTPS port. |
| `WEBAPP_AUTOPILOT_ALLOW_INSECURE_LOCAL` | `false` | Test-only localhost HTTP exception. It must remain unset/false on Railway and production. |
| `WEBAPP_AUTOPILOT_MAX_RUN_SECONDS` | `20` | Shared Web/Cron wall-clock budget, valid from 1 through 25 seconds. |
| `WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN` | `20` | Web-only cap, valid from 1 through 20 local metadata actions per run. |
| `WEBAPP_AUTOPILOT_INCIDENT_RECOVERY_STREAK` | `3` | Consecutive signed ticks with a fresh `within_target` ordinary Web-support triage required before the local incident can close; valid only from 2 through 10. Invalid values produce a guarded receipt. |
| `WEBAPP_AUTOPILOT_TOPOLOGY` | unset | Web-only explicit acknowledgement. It must be exactly `sqlite_single_replica` before a tick can run against the current SQLite state. In `production`, `prod` or `live`, an explicit `RAILWAY_REPLICA_COUNT`, `RAILWAY_REPLICAS` or `WEBAPP_REPLICA_COUNT` attestation is required and must parse as exactly `1`. |

`WEBAPP_AUTOPILOT_ENABLED=true` exposes authenticated observation and the
internal scheduler endpoint. It does not itself permit metadata writes.
`WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED=true` additionally permits the
small allow-listed Web-native metadata flow documented below. Neither flag
grants provider, payment, wallet, Bot, deployment or messaging authority.

Invalid authentication/configuration (missing required secret after the
feature is enabled, stale timestamp, duplicate nonce, incorrect HMAC, invalid
content type, excess body or concurrent lease) fails closed. A correctly
signed tick received while `WEBAPP_AUTOPILOT_ENABLED=false` is deliberately a
bounded `guarded` receipt. The service retains only its nonce hash and a
minimal guarded run receipt for replay protection; it acquires no lease and
does not write support/customer metadata or execute a playbook. This keeps an
already-configured Cron healthy during a safe pause without allowing that same
signed request to run after the flag is re-enabled. Responses contain no
secret, stack trace, raw support narrative, payment detail or provider handle.
An invalid `WEBAPP_AUTOPILOT_MAX_RUN_SECONDS` or
`WEBAPP_AUTOPILOT_MAX_ACTIONS_PER_RUN` is also a nonce-consuming `guarded`
receipt, not an HTTP failure: this prevents a malformed Railway Cron setting
from repeatedly failing/retrying while still preserving replay protection.

## Internal tick authentication

The Cron service supplies exactly one each of `X-Ops-Timestamp`,
`X-Ops-Nonce`, `X-Ops-Request-Id`, `X-Ops-Signature` and `X-Ops-Key-Id`.
The key ID must equal the currently configured Web key ID. Signature material
is:

```text
method + "\n" + path + "\n" + timestamp + "\n" + nonce + "\n"
  + request_id + "\n" + key_id + "\n" + SHA256(body)
```

The body is the exact canonical UTF-8 JSON encoding (sorted keys, no
whitespace) of:

```json
{"protocol_version":1,"requested_at":"<X-Ops-Timestamp>","trigger":"railway_cron"}
```

It must be at most 8 KiB; the timestamp must be timezone-aware, equal the
signed header value and within 300 seconds of the Web clock. The nonce must
match the protocol pattern and is retained as a hash for 600 seconds. Request
IDs are UUIDs and are bound to a unique run. The Web service verifies HMAC
with `hmac.compare_digest` before persisting the nonce. A topology/config or
disabled-feature guard still writes a minimal `guarded` replay receipt; only a
ready tick acquires a single-owner lease/fencing token. A replay never runs a
second remediation, even if configuration changes during the clock-skew
window.

The Cron runner pins the configured origin, disables proxies, rejects every
redirect and accepts only a bounded JSON response whose `data.request_id`
matches its signed request. It never logs the Web response payload. It exits
successfully only for the accepted `completed`, `guarded` or `read_only`
statuses; a configuration or transport/contract failure exits non-zero.

## State model

| Record | States |
| --- | --- |
| Autopilot run | Implemented: `started → completed | guarded | failed`. If a process dies and its lease expires, the next authenticated tick fences that exact old `started` receipt to `guarded` with `OPS_TICK_LEASE_EXPIRED` before it takes over. This changes no source case or external authority. `timed_out` is reserved, not currently written. |
| Incident | Implemented: SLA-breach records use `open` and later `investigating` when observed again. When its source Support Desk case reaches `resolved` or `closed`, a bounded local reconciliation can set the local Operations incident to `closed`; it does not change the source case or any external system. `mitigated` and `resolved` are reserved. |
| Approval action | Implemented: `awaiting_approval → approved | rejected | expired`; terminal-case reconciliation can set a still-pending record to `superseded`. Every decision and expiry transition remains record-only. `proposed`, `executed` and `guarded` are reserved. |
| Complaint triage | Implemented as owner-scoped metadata with a `disposition` of `awaiting_operator`, `monitored` or `terminal_monitoring`; it is not yet a separate persisted state machine. |

No Operations record is silently deleted by the current implementation. No
retention or archival worker is implemented yet; a future retention design
must be explicitly documented, reviewed and audited before it deletes or
archives anything.

## Safe automatic playbooks

After both feature flags are enabled, these are the only automatic actions
implemented in this release:

1. Verify local database readiness with a bounded read-only probe.
2. Recompute a complaint SLA/advisory status from Support Desk category,
   priority, state, the semantic customer-waiting clock and revision only. It
   does not read or copy the ticket subject, detail or messages.
3. Upsert a keyed-fingerprint SLA-breach incident for a triaged case without
   changing customer-visible content.
4. Create one approval proposal per relevant case revision; this never runs
   the proposed financial, provider or delivery action.
5. Reconcile only local Operations metadata after a Support Desk case is
   already terminal: retain its terminal triage, close matching local
   incidents and supersede pending local approval records. It never changes
   the Support Desk case, contacts the customer or invokes an external system.
6. Reconcile the expiry time of a still-pending local approval record. This
   only changes its local state to `expired` and appends its audit event; it
   cannot execute, retry, cancel or otherwise affect the named external,
   financial, delivery or deployment action.
7. Reconcile a prior `support_sla_breach` incident only after the scheduler
   re-reads its current non-terminal Support Desk case and observes fresh
   `within_target` triage for the configured consecutive-tick threshold. The
   case must remain ordinary `web_support`, match the incident account, and
   have no awaiting local approval. A breach, stale/invalid customer-waiting
   clock,
   reopen, financial/provider/unclassified risk, account mismatch or pending
   approval resets/holds the local streak. This playbook changes only the
   local Operations incident and its compact observations; it does not close
   the Support Desk case, send a message, retry a job or call Bot/provider/
   PayOS/wallet/deployment systems.
8. When the separately gated Reliability Follow-up contract is enabled,
   materialize only sanitized runtime/complaint follow-up metadata and prune
   its old route-family buckets. It cannot inspect raw logs, repair code,
   restart Railway, call Bot/provider/payment/wallet/job, freeze a feature or
   contact a customer. See [`WEB_RELIABILITY_FOLLOWUP_CONTRACT.md`](WEB_RELIABILITY_FOLLOWUP_CONTRACT.md).

Each accepted run has a deadline, action budget, nonce/request id, fencing
token, input hash and compact receipt. Triage writes are idempotent on source
revision plus policy input hash. The runner stores only capped, non-sensitive
metadata and opaque HMAC fingerprints.

If a run reaches its action budget after triage but before a required local
incident or approval proposal is created, a later bounded tick reconciles only
the missing local follow-up. It does not create repeat observations or repeat
proposals for an already-linked case/revision.

The policy names `incident_dedupe`, retry/backoff, generic playbook freezing
after repeated failures and Workboard marker creation are **reserved future
playbooks**. They must not be advertised as
automatic remediation until an implementation, tests, runbook and review are
added.

## Actions that always require approval

The following must create an approval record but cannot be performed by a tick:

| Category | Examples |
| --- | --- |
| Financial | Xu adjustment, top-up verification, PayOS finalization, refund, price/package/promo change. |
| External | Provider/Bot call, publish, campaign send, Telegram/email/SMS reply, external webhook. |
| Delivery | Retry canonical job, deliver/download output, modify customer asset. |
| Security/data | Role change, secret/ENV change, deletion, backup restore, account merge, session revocation at scale. |
| Deployment | Code patch, Git merge, Railway config/deploy/restart. |

An approval requires a signed Web session, canonical server-side Support role,
CSRF, explicit confirmation, decision code, idempotency key, optimistic
revision and an audit event. `support_operator` may read the queue;
`support_manager` and Web admin may decide it. Browser-supplied role/identity
is never trusted.

## Complaint triage

The existing Web Support Desk remains the source of cases and public messages.
Autopilot deterministically classifies the already-selected category, priority,
age, state and revision into:

- SLA target and breach advisory;
- duplicate case candidate (never auto-close or merge);
- affected Web module/incident linkage;
- next internal checklist and required operator role;
- `awaiting_operator` for finance, provider, security or account-impacting
  complaints.

It does not write a public customer reply, claim a refund, claim a provider
outcome or present a fake resolution. A future reply adapter must be separately
approved and implement consent, templates, rate limits, human override and
delivery receipts.

### Semantic customer-waiting clock

`web_support_cases.customer_waiting_since` is the only source of SLA age for
active cases. It is deliberately **not** `updated_at`: managers may assign a
case, update an internal queue/SLA class, add a private note, or record an
internal escalation without providing a customer-visible response.

- Case creation, a customer reply, and a customer reopening a terminal case
  establish a new customer-waiting clock.
- A public operator reply clears the clock because the next turn belongs to
  the customer. An internal operator note does not change it.
- Internal triage, assignment, escalation and non-terminal status metadata
  preserve the clock. A terminal `resolved`/`closed` state clears it.
- Legacy records with no semantic clock are shown to Operations as
  `unverified`; they can never create a new automatic SLA-breach incident or
  count as a healthy tick toward automatic incident closure. A human can
  handle them normally, and the next genuine customer-waiting event establishes
  a safe clock. When the separate Web Reliability Follow-up gate is enabled,
  an active ordinary Web Support record with this status may create one bounded
  medium local staff follow-up; it remains neither an incident nor a customer
  notification, and it never mutates the source case.

This prevents internal staff activity from falsely resetting, satisfying, or
closing a customer SLA. The clock has no Telegram, email, provider, wallet,
PayOS, Bot, job or notification effect.

## Data model (additive only)

The implementation will add account-safe, append-oriented tables:

- `web_ops_runs`, `web_ops_run_steps`, `web_ops_leases`, `web_ops_nonces`;
- `web_ops_incidents`, `web_ops_incident_observations`, `web_ops_playbook_runs`;
- `web_ops_approvals`, `web_ops_approval_events`;
- `web_support_triage` and `web_support_triage_events`.
- Reliability-only: `web_ops_runtime_signal_buckets`,
  `web_ops_runtime_signal_totals`, `web_ops_followups` and
  `web_ops_followup_events`.

Sensitive narrative is never copied to routine telemetry. Persisted details are
limited to IDs, bounded policy metadata, hashes/fingerprints and timestamps.
All rows use server-generated UUIDs, owner/operator checks and existing Web
audit conventions.

## API and UI boundary

Customer-safe reads:

```text
GET /api/v1/operations/status
GET /api/v1/operations/incidents
GET /api/v1/support/cases/{id}/triage
```

Staff-only operations:

```text
GET  /api/v1/operations/admin/summary
GET  /api/v1/operations/admin/incidents
GET  /api/v1/operations/admin/runs
GET  /api/v1/operations/admin/approvals
POST /api/v1/operations/admin/approvals/{id}/approve
POST /api/v1/operations/admin/approvals/{id}/reject
GET  /api/v1/operations/admin/reliability/summary
GET  /api/v1/operations/admin/followups
GET  /api/v1/operations/admin/followups/{id}/handoff
POST /api/v1/operations/admin/followups/{id}/acknowledge
POST /api/v1/operations/admin/followups/{id}/resolve
POST /api/v1/operations/admin/followups/{id}/reopen
POST /internal/v1/operations/tick
```

Successful Operations responses and explicit Operations guarded responses
include a truthful execution boundary. Generic framework validation/denial
responses remain normalized API envelopes, but callers must not infer a repair
or external result from them. The UI renders observed state and never
fabricates a completed repair, external delivery, payment or provider result.

## Railway deployment contract

`/health` remains only a deploy readiness endpoint; it is not continuous
production monitoring. A separate Railway Cron service invokes the
authenticated tick and exits. Railway Cron schedules use UTC, have a minimum
five-minute interval, do not promise minute-exact execution and skip a
scheduled execution if the previous Cron process is still active. These
platform constraints are documented by
[Railway Cron Jobs](https://docs.railway.com/cron-jobs). The runner must use
the short-lived command:

```text
python scripts/operations/run_autopilot_tick.py
```

Start with `*/5 * * * *` only after the Web service is healthy and use a
schedule no tighter than the implementation can tolerate. The Cron service
must not mount the Web SQLite volume and must receive only
`WEBAPP_AUTOPILOT_TICK_URL`, `WEBAPP_AUTOPILOT_TICK_ORIGIN`,
`WEBAPP_AUTOPILOT_TICK_SECRET`, `WEBAPP_AUTOPILOT_TICK_KEY_ID` and the shared
`WEBAPP_AUTOPILOT_MAX_RUN_SECONDS`. The **Web** service (not the Cron service)
must also hold `WEBAPP_AUTOPILOT_TOPOLOGY=sqlite_single_replica` and any
explicit replica-count value must equal `1`. Do not give the Cron service
`WEB_SESSION_SECRET`, a database path/volume, Bot, PayOS, wallet, provider or
incident-fingerprint secret.

Safe enablement is phased and explicit:

1. Deploy with both Autopilot flags `false`; confirm the Web service uses its
   persistent SQLite volume, its resolved `WEBAPP_SESSION_DB_PATH` is under
   that mount, and it has one replica. Set the Web-only topology
   acknowledgement `WEBAPP_AUTOPILOT_TOPOLOGY=sqlite_single_replica` only
   after that confirmation.
2. Set `WEBAPP_AUTOPILOT_ENABLED=true`, configure the Web HMAC secrets/key ID,
   keep `WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED=false`, and review the
   authenticated portal/read API behavior.
3. Create the isolated Cron service with the exact pinned URL/origin and only
   its minimal variables. Observe several `guarded` health-only runs.
4. Only after review, set safe remediation true on the **Web service** and set
   `WEBAPP_AUTOPILOT_INCIDENT_SECRET`; this enables metadata triage, incident
   records and approval proposals only.

Rollback is also explicit: first set
`WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED=false` (health-only guarded runs),
then disable the Cron service or set `WEBAPP_AUTOPILOT_ENABLED=false`. Never
delete Operations/audit rows to roll back. Because the current one-key setup
has no dual-key grace period, rotate tick secrets/key IDs only in a planned
window in which Web and Cron are changed together.

Enabling the Cron service, changing its schedule, setting secret references,
scaling replicas or deploying/restarting Railway are deployment operations,
never implicit side effects of a Web code merge or Autopilot tick.
