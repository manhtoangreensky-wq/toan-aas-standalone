# Admin ERP Operations Desk read-model contract

## Purpose

`/admin/work-queue` is a compact, read-only coordination view for the
standalone Web App.  It is not a new Bot, provider, wallet, payment, job,
delivery or deployment control plane.  Each destination remains responsible
for its own staff authorization and its own write contract.

The Desk exposes only these server-owned source kinds, in this receipt order:

1. `support_case`
2. `operations_incident`
3. `operations_approval`
4. `reliability_followup`
5. `content_handoff`

The API is signed-session staff-only.  Its browser projection contains only
kind, enum state, enum priority/severity and an ISO timestamp or
`"unavailable"`.  It deliberately retains no record ID, account, email,
title, detail, payload, server target, action label, query-by-ID field or
write instruction.

## Receipt and fail-closed rules

- The summary must return the exact five source receipts in canonical order.
- A source marked `available` must have a bounded integer count.  A
  `guarded` or `unavailable` source must have a `null` count; zero is never
  used to stand in for an unknown source.
- `partial` must exactly agree with the source availability receipt.  The
  summary and filtered list must agree on that partial status and the API
  envelope status (`read_only` or `guarded`).
- Each listed row must have a canonical kind/state/level/timestamp, canonical
  destination receipt and one bounded action receipt before the client drops
  the destination and action text from portal state.
- Counts, offsets, `returned`, `has_more`, `next_offset` and the previous
  offset must agree with the receipt.  A malformed 2xx response, dropped row,
  unexpected source, duplicate source, mismatched count or malformed page is
  a failed read, not an empty queue.
- A fresh signed read clears the previous Operations Desk projection before
  loading.  A failure leaves no stale staff queue, browser role or Bot
  fallback visible.  The user receives a clear manual `Thử tải lại` action;
  the Desk never self-retries or changes operational state.

## Security and delivery boundaries

- Authorization remains server-side through the signed session and canonical
  staff role.  Browser state, local storage, Telegram ID and query strings
  cannot grant a Desk capability.
- The route uses allow-listed enum filters only.  It has no free-text search,
  record ID, arbitrary sort, assignment, retry, refund, freeze, upload,
  download or write action.
- The UI derives destination links from a local allow-list after validation;
  it does not retain a server URL or action label in portal state.
- Operations Desk data is private application state.  It is excluded from
  public PWA shell caching and must be refreshed through a signed request.
- This module makes no Bot/core bridge, provider, PayOS, Xu wallet, job,
  delivery, payment webhook or deployment call.

## Verification scope

Focused contracts cover signed staff authorization, source availability,
server-side filters/pagination, redacted rows, strict client receipts,
stale-state clearing, recovery UI, CSRF/session ownership boundaries and
JavaScript syntax.  They intentionally use mocked/local Web records only;
they do not invoke Telegram, PayOS or paid providers.
