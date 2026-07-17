# Web Data Control Center contract (v1)

## Purpose and boundary

The Data Control Center is a **Web App-only** privacy control.  It is disabled
unless `WEBAPP_DATA_CONTROLS_ENABLED=true` is set.  It does not read, write,
proxy, or reconcile data owned by the Telegram Bot or a payment/provider
system.

The first release is deliberately narrow and honest:

- it can directly download a bounded, private JSON copy of Web-authored
  profile, Memory, Prompt Library, and Workboard data;
- it can create or cancel an erasure *review request* for that same Web
  authoring scope;
- it cannot automatically delete data, claim that a third party has been
  erased, or create a background export job.

Requests use the policy version `web_data_controls_v1`.  The only erasure
scope is `web_authoring_only`.

## Explicit exclusions

The export and erasure request do not include, alter, or promise deletion of:

- Telegram/Bot identity, conversations, bridge state, or Telegram delivery;
- Xu ledger, PayOS payments/webhooks, packages, refunds, or billing records;
- provider configuration, provider jobs, generated assets, delivery outputs,
  or provider-hosted data;
- passwords, sessions, OAuth credentials, API keys, security events, or raw
  append-only audits;
- support evidence/internal notes, Operations Desk/Reliability data,
  notifications, CRM/third-party data, Asset Vault blobs, or package/operation
  artifacts.

These systems have their own retention, ownership, and operational controls.
The Web App must not imply otherwise.

## API and security contract

All endpoints are under `/api/v1/account/data-controls`, require a signed Web
session and CSRF for writes, and are scoped server-side to the signed account.
The service writes minimal audit records (counts, identifiers, policy and
outcome), never exported customer content.

| Endpoint | Purpose |
| --- | --- |
| `GET /summary` | Returns availability, scope, policy, exclusions and current-request summary. |
| `GET /requests` | Returns the signed account's own erasure requests. |
| `POST /export.json` | Downloads a direct bounded JSON attachment after explicit confirmation. The response is private/no-store and is never retained as an export job. |
| `POST /erasure-requests` | Creates an idempotent staged review request only. |
| `POST /erasure-requests/{request_id}/cancel` | Cancels the signed account's eligible request with an expected revision. |

The export request must carry `policy_version: "web_data_controls_v1"` and
`confirm: true`.  An erasure request additionally requires
`scope_key: "web_authoring_only"`, `confirm: true`, a unique idempotency key,
and acknowledgement text `REQUEST WEB AUTHORING ERASURE`.  Cancellation uses
`CANCEL WEB ERASURE REQUEST` plus the expected revision.

The direct attachment has a strict 8,000-record / 12 MiB ceiling. It performs
count and source-byte preflight before materialising rows, then applies the
exact cap during incremental JSON encoding; it returns a guarded envelope,
never a partial download, when either ceiling is exceeded. The service also
applies small body limits and independent read/write/export rate limits. Hidden
or another account's request is represented by a generic response; the caller
must not learn whether it exists.

## Review workflow

New requests are either `awaiting_review` where a suitable account verification
factor exists, or `identity_verification_pending` otherwise.  Neither state
deletes any data.  A reviewer must verify identity, retention blockers and
scope before any future separate deletion workflow is introduced.  The account
may cancel an eligible request; revision and idempotency controls protect
against duplicate or stale actions. Only one live erasure request can exist for
an account and this scope at a time, so changing an idempotency key cannot
create an unbounded queue of equivalent requests.

## PWA and deployment

The account page and every Data Control API route are private.  The service
worker must never cache them, nor cache the direct download.  Production use is
off by default and requires an explicit environment setting plus an operational
review; enabling this feature does not authorize provider, Bot, or payment
operations.
