# ERP Operations Desk contract

`/api/v1/admin/operations-desk` is a Web-native, read-only staff queue. It
aggregates only persisted metadata from Support Desk, Operations incidents and
approvals, Reliability Follow-up, and Content Handoff. It does not call the
Bot/Core Bridge, a provider, PayOS, wallet/Xu, jobs, delivery or deploy APIs.

Both endpoints require a signed Web account with the existing Support staff
authority (`admin`, `support_manager`, or `support_operator`):

- `GET /summary` returns source availability and counts.
- `GET /work-items?view=&kind=&state=&severity=&limit=&offset=` returns a
  bounded, deterministic page. Filters are fixed allowlists; there is no
  free-text, ID, account or target-route search.

Every item contains only a source kind, a server-allowlisted admin route,
state, priority/severity, safe timestamp and descriptive read/navigation
labels. IDs, accounts, emails, customer text, support/content details,
canonical/request/audit IDs, payment/provider/job data and source payloads
are never returned.

`WEBAPP_ADMIN_ERP_ENABLED=false` guards the entire desk before source reads.
If an underlying feature is disabled, lacks its required Reliability
preflight, or its table is unavailable, that source is reported as
`guarded`/`unavailable` with a `null` count and the overall response is
`guarded`; it is never reported as a healthy zero queue.

## Exception lane

`view=all` is the default list. `view=attention` is a server-owned, read-only
exception lane; it is applied inside each source query before `COUNT`, ordering
and pagination. The browser can request only `all` or `attention`, and cannot
provide a record ID, account, assignment, text, provider or payment value that
changes the lane.

The fixed policy is intentionally narrow:

- Support: active high/urgent items, or `new`, `reviewing` and
  `refund_pending` items; `resolved` and `closed` stay out.
- Operations: `open` and `investigating` incidents.
- Approvals: `awaiting_approval` only.
- Reliability: `open` and `acknowledged` follow-ups.
- Content Handoff: `review`, `approved_for_handoff` and `blocked` records.

`requested` is Customer Care escalation metadata, not an Operations Desk state,
so this lane does not query or infer it. `guarded`, `unavailable`, malformed
enum values and terminal records are never promoted into an exception or a
healthy zero. The summary endpoint deliberately remains an all-source
availability/count view; it is not reinterpreted as the current exception-lane
total.

## Portal handoff

`/admin/work-queue` is issued in the server-side Admin ERP navigation only to
the existing Web Support roles. Its HTML route and both JSON reads repeat the
same signed server-side role check; a browser role, Telegram ID, query string
or cached navigation cannot unlock it.

The Portal makes two GET reads and keeps only an allowlisted projection:
source kind, availability, nullable count, state, priority/severity and safe
timestamp. It discards all identifiers, account/customer fields, content,
source payload, server action labels and remote target route. The displayed
route is mapped again from a fixed client constant. The Desk itself contains
only refresh/filter/paging actions; its “Cần xử lý” view is a filter, not an
auto-remediation promise. It cannot write, retry, refund, freeze, assign,
upload, download, call Bot/Core Bridge/provider/PayOS/wallet/job/delivery APIs,
deploy or run an automation.

A dedicated session and request epoch fence invalidates delayed responses on
logout, account switch, feature disablement, route change and newer filter
read. A successful partial `guarded` envelope may show its own redacted source
metadata, but any malformed/failed/unauthorized read clears the Desk rather
than rendering a prior staff queue or inventing zero counts.
