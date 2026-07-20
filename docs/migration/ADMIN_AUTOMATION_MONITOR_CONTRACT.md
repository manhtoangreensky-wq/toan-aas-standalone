# Admin Automation Monitor contract

`/admin/automation` is a Web-native, read-only ERP screen for the existing
Inbox scheduler receipt table. It is an operator observability surface, not a
scheduler control plane and not a Bot parity claim.

## Authority and availability

- The HTML route and both JSON routes require a signed Web session with the
  server-side local `admin` role. The browser never supplies an admin ID,
  Telegram ID, role, source ID, or run identifier.
- `WEBAPP_ADMIN_ERP_ENABLED` is the directory kill switch. When it is off,
  endpoints return a stable `guarded` empty projection and make no receipt DB
  query.
- `WEBAPP_NOTIFICATION_CENTER_ENABLED=false` also yields a stable guarded,
  empty projection and makes no receipt DB query.
- `WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=false` is a truthful observation
  state: historical redacted receipts may be read, but the response stays
  `guarded` and the screen never implies the scheduler will run.
- The feature is Web-local. It does not need or confer Bot canonical admin,
  Telegram identity, Core Bridge, provider, wallet/Xu, PayOS, job or deploy
  authority.

## Read-only endpoints

```text
GET /api/v1/admin/automation/summary
GET /api/v1/admin/automation/runs?limit=25&offset=0
```

Both return the standard envelope. `summary` returns only:

```json
{
  "scheduler": {
    "center_enabled": true,
    "automation_enabled": false,
    "state": "ready|center_disabled|automation_disabled|persistent_store_unverified|topology_unverified|single_replica_required|limits_unverified|guarded"
  },
  "latest_run": {
    "state": "started|completed|failed|guarded",
    "action_count": 0,
    "candidate_count": 0,
    "started_at": "2026-07-20T00:00:00+00:00",
    "finished_at": null
  },
  "run_counts": {
    "started": 0,
    "completed": 0,
    "failed": 0,
    "guarded": 0,
    "unknown": 0
  },
  "integrity_guarded": false
}
```

`runs` returns an `items` list of exactly the same redacted run projection,
plus bounded pagination (`limit` 1–50; `offset` 0–10,000). There is no search,
filter, total count, run detail or cursor endpoint.

The only receipt fields selected or returned are `state`, `action_count`,
`candidate_count`, `started_at`, and `finished_at` from
`web_notification_runs`. The database may use the opaque run ID only as an
internal stable sort tie-breaker; it is never selected, returned, searched,
or exposed to the Portal. The monitor never reads nonce, lease, step, item,
event, dedupe, source or account tables. It also never performs DDL or opens
a scheduler/write transaction; schema creation remains application startup
responsibility. Before any aggregate is shown, the server validates the exact
five-field receipt projection across a fixed safe scan window. A malformed
row, or a retained history too large to validate within that fixed bound,
keeps the response `guarded` instead of publishing a partial healthy count.

## Deliberate redaction and prohibited actions

The JSON/API/Portal must not expose or infer run ID, request ID, schedule slot,
trigger, fence token, policy/input hash, deadline, error code, receipt JSON,
nonce, HMAC, lease, source/account/customer data, raw configuration, logs or
stack trace.

There is intentionally no POST/PATCH/DELETE route, CSRF write action, tick
button, scheduler configuration, retry, webhook, provider call, notification
send, Bot/Core Bridge call, wallet/Xu/PayOS action, job mutation, download,
secret change, restart, deploy, feature freeze or self-modifying behavior.

The Portal uses a dedicated session/route hydration epoch and `cache: "no-store"`.
It clears the whole projection after logout, account switch, feature disablement,
navigation or a failed response. The service worker already excludes broad
`/admin` and `/api/v1/admin` paths from Cache Storage.

## Operational interpretation

`completed` means only that a bounded Web scheduler receipt reached its own
terminal state. It does **not** mean a customer was contacted, Telegram/email/
web-push was sent, a provider/job/payment action happened, or any defect was
automatically repaired. A malformed persisted receipt is dropped from the
rendered list and changes the response/page to `guarded` rather than becoming
a fabricated zero/healthy result. In that state `integrity_guarded` is true:
Portal keeps the scheduler/read boundary visible but hides aggregate numeric
counters rather than representing partial SQL state buckets as verified data.
