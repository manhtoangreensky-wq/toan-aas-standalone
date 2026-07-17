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

`report_file_created: false` remains true for the normal JSON API contract.
The narrowly gated CSV attachment described below is assembled in memory for
the current response only; it is not a stored report file, Asset Vault item,
job, delivery record or canonical report.

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

### Narrow finalized CSV attachment

This one route is deliberately separate from the generic mutation contract:

```text
POST /api/v1/analytics-workspace/reports/{report_id}/export.csv
body: { "expected_revision": <positive integer> }
```

It is available only when both the Analytics Workspace and the separate
`WEBAPP_ANALYTICS_WORKSPACE_EXPORT_ENABLED` flag are enabled. The export flag
defaults to `false`; enabling authoring with
`WEBAPP_ANALYTICS_WORKSPACE_ENABLED` does not enable attachments.

The request requires the signed Web session and CSRF token. The server resolves
the report through that signed account, requires its current lifecycle state to
be `finalized`, requires the supplied metadata revision to match, then checks
the same ownership, state and revision again immediately before recording the
minimal audit receipt and releasing the response. A missing cross-account
report is not disclosed. A stale, reopened or non-finalized report returns a
guarded JSON response rather than an attachment.

This route is a manual Web-data attachment only. It is not `/campaign/report`,
a Bot campaign report, a platform export, a provider result, a revenue/Xu/PayOS
record or a generic report/PDF delivery API. The Bot remains canonical for its
own campaign report and parity mapping; this Web-native route does not change
that boundary.

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

All accepted text rejects control characters, credentials, token-like values,
OTP/card or payment evidence, Bot/provider/job/file handles, executable
markup, URLs, browser schemes and local/UNC paths. Short line-like fields
also reject spreadsheet-formula prefixes; narrative fields remain
human-authored text and are independently neutralized again at CSV assembly.
The API does not support CSV import, file upload, external URL import, a
generic report-file export or PDF delivery.

The sole CSV exception is the finalized manual attachment route above. Its
source is read afresh on the server from only the signed owner's **active**
manual report, metric, snapshot and finding records; the browser never builds
or supplies CSV rows. The fixed CSV schema intentionally excludes account IDs,
report IDs, project/campaign references, event/audit data and any Bot,
platform, provider, wallet, payment, job or delivery data. It uses UTF-8 with
a BOM and CRLF rows, and applies formula-injection protection again to every
cell that begins (including after whitespace or common invisible format
prefixes) with `=`, `+`, `-` or `@`.

The attachment is bounded to 24 MiB and a 32,000-row serializer limit. The
server first counts the exact active owner-scoped query shapes and then streams
their cursors through the byte-capped serializer; it does not materialize a
full legacy report in process memory. If the complete result would exceed a
bound, the server returns a guarded `413` response and emits no partial file.
The finalized-revision audit recheck has a short bounded SQLite write window;
contention returns a sanitized `503` with no attachment. It is returned only
as the immediate response: no CSV blob is retained in SQLite, Asset Vault, PWA
cache, browser storage, job, asset or output-delivery table. The response carries
`Cache-Control: no-store, private`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `Content-Security-Policy: sandbox` and
same-origin resource isolation headers. The application assigns this exact
POST route its own `analytics-workspace-manual-csv-export` rate-limit scope of
10 requests per client IP per minute before CSRF, owner lookup, SQLite reads
or attachment assembly.

Private `/analytics` and `/api/v1/analytics-workspace` paths are excluded from
the PWA cache. The browser holds no report/snapshot/finding content in
localStorage and rehydrates from the signed server after a mutation receipt.

## Known guarded gap

Platform synchronization, verified social metrics, AI analysis, revenue and
cost attribution, Bot reports, file/CSV import, canonical/generic export or
PDF delivery, publishing and provider integrations require separate
Web-native adapter contracts. They must define authority, consent, secret
handling, costs, ownership, validation, audit and delivery before any
connection is enabled. The narrow finalized manual CSV attachment above is
not such an adapter and must not be represented as one.
