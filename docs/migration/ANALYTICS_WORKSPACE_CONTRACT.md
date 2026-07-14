# Analytics Workspace — Web-native contract

## Scope

`/analytics`, `/analytics/new`, and `/analytics/{report_id}` are a private,
signed-account workspace for recording and reviewing manual measurements. They
own only Web-account records:

- a report: title, measurement objective, period, optional Web Project or
  Campaign Planner reference, tags, summary note, lifecycle and metadata
  revision;
- metric definitions: name, unit, evaluation direction and description;
- snapshots: a date, non-negative decimal value, a self-declared source label
  and note; and
- human-authored findings, decisions and actions.

This is not a social-media connector, dashboard mirror, platform analytics
API, Bot report, provider report, revenue ledger, Xu wallet, payment,
publishing or generated-report surface.

## Explicit trust boundary

Every Analytics API response declares:

```text
execution: manual_measurement_only
data_origin: user_supplied_only
local_calculation: true
bot_called/provider_called/social_api_called: false
platform_data_connected/platform_data_verified: false
ai_recommendation_created: false
canonical_revenue/wallet_mutated/payment_*: false
job_created/publish_action_created: false
browser_file_upload/external_url_import/report_file_created: false
output_delivery: not_applicable
```

The source label is an account-authored description, not verification or a
connection. The browser and server must never imply that a number came from
TikTok, Facebook, YouTube, a provider, the Telegram Bot or a canonical
financial system.

## API

Read API is owner-scoped and returns `no-store, private` responses:

```text
GET /api/v1/analytics-workspace/summary
GET /api/v1/analytics-workspace/policy
GET /api/v1/analytics-workspace/references
GET /api/v1/analytics-workspace/reports
GET /api/v1/analytics-workspace/reports/{report_id}
GET /api/v1/analytics-workspace/reports/{report_id}/events
```

Writes require a signed session, CSRF token, server-side account ownership,
optimistic revision and a scoped idempotency key:

```text
POST  /api/v1/analytics-workspace/reports
PATCH /api/v1/analytics-workspace/reports/{report_id}
POST  /api/v1/analytics-workspace/reports/{report_id}/lifecycle
POST  /api/v1/analytics-workspace/reports/{report_id}/restore-version

POST  /api/v1/analytics-workspace/reports/{report_id}/metrics
PATCH /api/v1/analytics-workspace/reports/{report_id}/metrics/{metric_id}
POST  /api/v1/analytics-workspace/reports/{report_id}/metrics/{metric_id}/state

POST  /api/v1/analytics-workspace/reports/{report_id}/metrics/{metric_id}/snapshots
PATCH /api/v1/analytics-workspace/reports/{report_id}/metrics/{metric_id}/snapshots/{snapshot_id}
POST  /api/v1/analytics-workspace/reports/{report_id}/metrics/{metric_id}/snapshots/{snapshot_id}/state

POST  /api/v1/analytics-workspace/reports/{report_id}/findings
PATCH /api/v1/analytics-workspace/reports/{report_id}/findings/{finding_id}
POST  /api/v1/analytics-workspace/reports/{report_id}/findings/{finding_id}/state
```

Mutation receipts retain opaque identifiers, revision/state and the explicit
boundary only. They never retain report objective, notes, snapshot source,
snapshot value or finding narrative in `web_idempotency`.

## Lifecycle and revisions

Report lifecycle permits only these server-checked transitions:

```text
draft → review | archived
review → draft | finalized | archived
finalized → draft | review | archived
archived → draft
```

Only `draft` permits report metadata and child-record mutation. `review`,
`finalized` and `archived` remain readable but return a guarded result for
new/edit/archive/restore metric, snapshot or finding requests. Restoring a
metadata version always creates a new Draft revision and leaves child history
unchanged.

Report metadata/lifecycle revisions are distinct from child revisions. A
metric, snapshot or finding carries its own revision; its write checks both
its own expected revision and the current report revision, but does not
silently advance the report metadata revision. This lets independently edited
manual observations retain their own auditable history without making a
metadata form stale after every child write.

## Manual calculation rules

Snapshots accept an ordinary, finite, non-negative decimal only — no formula
prefix, exponent notation, negative value, `NaN` or infinity. The server
normalizes stored text using `Decimal`; it does not use binary float
arithmetic. For each active metric it calculates only from saved active
snapshots:

- latest and previous values, ordered by observation date then record ID;
- `delta = latest - previous`; and
- `change_percent = delta / previous * 100` only when previous is non-zero.

The comparison is absent rather than invented when there is no prior usable
value. One active snapshot per metric/date is enforced; archive it before
recording a replacement for that same date.

## Data, limits and safety

The additive SQLite tables are:

```text
web_analytics_reports
web_analytics_report_versions
web_analytics_metrics
web_analytics_metric_versions
web_analytics_snapshots
web_analytics_snapshot_versions
web_analytics_findings
web_analytics_finding_versions
web_analytics_workspace_events
```

All rows include `account_id`; every read/write resolves the parent report and
child record through that account. Additive schema initialization performs no
destructive migration.

The API bounds data before parsing or SQLite work: 128 KiB raw JSON per write,
300 reports/account, 60 metrics/report, 500 snapshots/metric, 300
findings/report, 100 report versions and 80 versions per child entity.
Version pruning is bounded retention for a single private record, not a schema
migration or a rollback of current state. Idempotency receipts are account
scoped, fingerprinted, redacted and retained for a short bounded window.

Text rejects control characters, credentials, token-like values, OTP/card or
payment evidence, Bot/provider/job/file handles, executable markup, URLs,
browser schemes, local/UNC paths and spreadsheet-formula prefixes. The API
does not support CSV import, file upload, external URL import or export.

Private `/analytics` and `/api/v1/analytics-workspace` paths are excluded from
the PWA cache. The browser holds no report/snapshot/finding content in
localStorage and rehydrates from the signed server after a mutation receipt.

## Known guarded gap

Platform synchronization, verified social metrics, AI analysis, revenue and
cost attribution, Bot reports, file/CSV import, export/PDF delivery,
publishing and provider integrations require separate Web-native adapter
contracts. They must define authority, consent, secret handling, costs,
ownership, validation, audit and delivery before any connection is enabled.
