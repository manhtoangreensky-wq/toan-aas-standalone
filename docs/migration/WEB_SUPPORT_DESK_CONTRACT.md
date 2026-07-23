# Web Support Desk & Ticket Center — Web-native contract

## Purpose and authority boundary

`/support`, `/tickets` and the dedicated `/admin/support` workspace turn the
useful support flow in the frozen Telegram Bot baseline into a signed,
professional Web service.  It is intentionally **Web-owned**.  Its tables
are named `web_support_*` and never read, write, migrate or mirror Bot
`support_tickets`, `support_ticket_messages` or Telegram conversation state.

| Surface | Owner | It never does |
| --- | --- | --- |
| Customer Support Desk | Signed Web account | Calls Bot, provider, PayOS, wallet/Xu, refund or job APIs; sends Telegram/email/push; accepts proof of payment or secrets. |
| Web Support operator workspace | Protected Web `role_cache` only | Accepts a browser-supplied role, raw Telegram ID or email/env allowlist as authorization; triggers a payment/refund/provider action. |
| Telegram Bot tickets and callbacks | Frozen Bot baseline | Appear in a Web case implicitly or receive Web case contents. |

The existing bridge compatibility endpoint `/api/v1/support/tickets` remains
unchanged for existing Bot-bound integrations.  It is not the primary Web
Support Desk API and no native case is silently handed over to it.

## Frozen Bot parity map

Static audit evidence is the frozen Bot SHA
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

| Bot capability | Web-native equivalent | Boundary / status |
| --- | --- | --- |
| `/support`, `/gopy`, ticket category choice | `/support` case composer with category, priority, subject and detail | Implemented as a private Web case; no Bot ticket is created. |
| `/tickets`, `/ticket_status` | `/tickets` list and `/tickets/{id}` immutable message/event timeline | Implemented for Web-owned cases only. Bot ticket history remains separate. |
| Bot customer reply conversation | Owner-scoped customer reply, close and reopen actions | Implemented with CSRF, revision and idempotency. |
| `/support_tickets`, `/support_ticket`, `/support_close`, `/ticket_admin` | `/admin/support` triage, staff-only case detail, public/internal reply and state/priority update | Implemented Web-native; no canonical refund, provider or Bot command is invoked. |
| Bot `new`, `reviewing`, `waiting_user`, `waiting_provider`, `refund_pending`, `resolved`, `closed` | Same state vocabulary | State is only a Web case lifecycle. `waiting_provider` never proves a provider call. |
| Bot SLA reports | Admin overdue metric (24h for new/review/refund, 72h waiting-provider) | Local Web calculation, not a Bot or provider SLA claim. |
| Telegram attachment/file ID flow and notifications | Asset Vault evidence link per Web case | Only an existing private Web Asset Vault PNG/JPEG/WebP/TXT can be linked; no Telegram file ID, raw Support upload, OCR, notification or external delivery. |
| Payment proof/refund/top-up requests | Category may be recorded, but no proof content is accepted | All TXID/bill/QR/account-number/manual-payment handling remains outside this Web module. |

## State and visibility model

```text
new -> reviewing -> waiting_user -> reviewing
                     \-> waiting_provider / refund_pending -> resolved -> closed
customer close: any non-closed state -> closed
customer reopen: resolved|closed -> reviewing
```

The operator may set a truthful Web lifecycle state after confirmation.  A
case is not marked as a payment/refund/provider success by this state; it is
only an internal support workflow state.

Messages have explicit visibility:

- `public`: customer and staff see it.
- `internal`: only staff see it.

Customer timelines expose only customer events and public operator replies;
they never expose internal notes, triage events or staff identities.  All
state data is owner-scoped even though case IDs are UUIDs.

## API contract

All writes require the signed session, CSRF header and an account/operator
scoped idempotency key.  New-case creation is the explicit exception to
revision/confirmation: `POST /api/v1/support/cases` creates revision `1` and
therefore has neither `expected_revision` nor `confirm`.  Every mutation of
an existing case carries optimistic `expected_revision`; customer replies do
not need a confirmation click, while close/reopen and every operator write
require `confirm: true`.  All responses use the common envelope.

```text
GET  /api/v1/support/summary
GET  /api/v1/support/advisor?category=
GET  /api/v1/support/cases?limit=&offset=&state=&category=&q=
POST /api/v1/support/cases
GET  /api/v1/support/cases/{case_id}
POST /api/v1/support/cases/{case_id}/attachments
GET  /api/v1/support/cases/{case_id}/attachments/{attachment_id}/download
POST /api/v1/support/cases/{case_id}/reply
POST /api/v1/support/cases/{case_id}/close
POST /api/v1/support/cases/{case_id}/reopen
GET  /api/v1/support/events

GET  /api/v1/support/admin/summary
GET  /api/v1/support/admin/cases?limit=&offset=&state=&category=&q=&team_queue=&assignment=&sla_class=&care_sla_status=&escalation_state=
GET  /api/v1/support/admin/cases/{case_id}
GET  /api/v1/support/admin/cases/{case_id}/attachments/{attachment_id}/download
POST /api/v1/support/admin/cases/{case_id}/reply
POST /api/v1/support/admin/cases/{case_id}/update
```

Lists use bounded `limit` and `offset`, returning `has_more` plus
`next_offset` when more results exist.  Browser state belongs to the mounted
Portal page and is not written to localStorage or passed to Telegram.

### Customer Care list filters

The staff list accepts only bounded Web-native metadata: `team_queue`
(`general`, `technical`, `account`, `creative`, `document`, `product`),
`assignment` (`all`, `mine`, `assigned`, `unassigned`), `sla_class` (`standard`,
`priority`, `critical`), `care_sla_status` (`all`, `unavailable`, `pending`,
`within_target`, `breached`, `overdue_unacknowledged`) and `escalation_state`
(`none`, `requested`, `acknowledged`, `resolved`, `cancelled`).  Cases without a
control row safely retain the defaults `general` / `unassigned` / `standard` /
`none`.

`assignment=mine` is resolved exclusively from the signed operator/manager
account on the server as `ctrl.assigned_account_id = account.id`; the browser
never receives or submits an assignee ID. It can be combined with every other
fixed Customer Care filter without turning the list into a staff-directory or
cross-account query.

`care_sla_status` is evaluated server-side before the bounded list's
`LIMIT`/`OFFSET`, using the same Web Customer Care **first staff touch** target
shown on a case (`24h` standard, `8h` priority, `2h` critical). It is a current
internal triage snapshot, not the separate customer-waiting report, Operations
Autopilot health state, a customer delivery promise or external notification.
The browser supplies no timestamp or clock; malformed `created_at` is surfaced
only by the `unavailable` fixed enum, while a missing/malformed first-touch
timestamp continues through the normal `pending`/`overdue_unacknowledged`
branch. No timer, case mutation or notification is created by filtering.

The list does not accept an assignee/account identifier, external queue,
provider, Bot, payment, ledger, system-clock or timestamp filter.  It returns an assignee display name
only; the internal assignee ID is available solely to a manager on the
case-specific detail read where the triage control needs it, while the
escalation reason remains case-detail-only.  The browser keeps the filter only in mounted page memory, offers
an explicit **Xóa lọc** action, and does not save staff search terms into
transient browser state.

## Support operator authorization

The only accepted roles are loaded from the server-side `web_accounts.role_cache`:

| Stored role | Support Desk permission |
| --- | --- |
| `admin`, `support_manager` | Manager: all current Support Desk reads/writes. |
| `support_operator` | Operator: all current Support Desk reads/writes. |
| anything else | Denied. |

Roles are provisioned by a protected deployment/administrator process in the
Web account store.  Email addresses, query parameters, request bodies, raw
Telegram IDs and environment email lists cannot grant the role.  `/admin/support`
uses this Web-only guard so it does not require Bot canonical admin access;
all other `/admin/*` routes retain their canonical Bot-admin guard.

## Security and privacy controls

- The router imports no Bot bridge and performs no HTTP/provider/PayOS/wallet/job call.
- Content is bounded and rejects API/GitHub/Google/AWS-style keys, bearer tokens,
  passwords, OTP/verification codes/CVV, every 13–19 digit card-shaped value
  (including spaces, repeated whitespace, dots, slashes or line breaks), and
  bill/TXID/mã GD/STK/bank-account/QR/payment-proof language. The server
  repeats this check for subject, customer reply, operator reply and internal
  note. Evidence does not accept bytes: it links an existing active owner
  Asset Vault item, requires a redaction attestation, allows at most three
  PNG/JPEG/WebP/TXT items up to 5 MB, rejects payment/refund/top-up category,
  scans TXT for the same secret/card/OTP/manual-payment patterns, and never
  claims image OCR.
- Every customer case query includes `account_id`; another account receives
  the same guarded not-found result without text leakage.
- Customer and operator writes are rate-limited before SQLite work, plus
  protected by CSRF, confirmation where meaningful, revision checks,
  idempotency collision detection and audit events.
- Audit records retain case UUID/action/coarse outcome only.  Subject, detail,
  customer reply, internal note and search text never enter the audit trail.
  A safe `operation_note` is stored instead as a staff-only timeline message.
- Non-closed cases are limited to 100 per customer; each timeline is bounded
  to 500 messages.  No mutation creates a fake delivery or outcome.
- PWA remains restricted to public shell assets; Support Desk routes/API and
  private timelines must never be cached.
- Evidence downloads re-check attachment → case → Asset Vault ownership and
  blob integrity server-side, use `no-store, private`, `nosniff`, no-referrer
  and CSP sandbox headers, and expose no public URL, storage path, hash,
  original filename or Asset Vault ID in events/audit records. Archiving the
  source Asset Vault item never makes evidence public or deletes it.

## Configuration and durability

```text
WEBAPP_SUPPORT_DESK_ENABLED=true
WEBAPP_ASSET_VAULT_ENABLED=true  # only required for evidence links/downloads
WEBAPP_SESSION_DB_PATH=<persistent-volume database path in production>
```

The desk defaults on because it has no paid/provider dependency.  Setting the
flag false returns a fail-closed maintenance response.  Like all Web-owned
data, production durability requires the already-configured persistent
session database volume.  This contract does not claim a Railway deployment,
live Bot integration, provider call, payment/refund or notification.

## Verification

Focused API/static Portal tests cover signed-session/CSRF enforcement,
idempotency, owner isolation, secret/manual-payment rejection, lifecycle
timestamps, private staff notes/events, role protection, disabled flag,
native UI/API boundary and service-worker non-caching.  Full regression and
static Bot audit run before merge; Telegram, PayOS and provider flows remain
mocked or out of scope.
