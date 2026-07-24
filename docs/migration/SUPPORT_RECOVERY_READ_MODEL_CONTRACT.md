# Support Recovery read-model contract

## Scope

This contract applies only to the customer-facing, Web-native Support Desk:

- `GET /api/v1/support/summary`
- `GET /api/v1/support/cases`
- `GET /api/v1/support/cases/{id}`
- `GET /api/v1/support/events`

It does not read Telegram ticket history, call a provider, create a job, mutate
the Xu ledger, create or finalise PayOS orders, or approve a refund.

## Signed-account boundary

The server remains authoritative for the signed account and ownership. A URL
case ID is never treated as proof of ownership. The browser clears prior case
data before every signed read and accepts the new projection only when the
current route and session epoch still match.

## Closed read receipts

`200 OK` is not enough to render private support content. The customer view
requires a closed Web-only receipt:

- summary contains all supported case states and an internally consistent
  active counter;
- list items are bounded, unique, typed cases with a valid owner-scoped pager;
- detail contains the requested case ID, public messages, customer-visible
  events and bounded Asset Vault evidence only;
- the `delivery` field is exactly `web_view_only`.

Malformed mandatory data fails closed: the UI clears the private projection,
marks it guarded and offers a fresh signed read. The independent activity feed
is optional; a failed or malformed activity receipt is shown as guarded rather
than as an empty history.

## Customer recovery presentation

Every validated case gets a deterministic next-step panel:

| Case state | Customer-facing guidance |
| --- | --- |
| `new`, `reviewing` | Keep one case; add context only when useful. |
| `waiting_user` | Add a safe response inside the same case. |
| `waiting_provider` | Do not resubmit work or infer a provider result. |
| `refund_pending` | No financial result is claimed or changed by the Web case. |
| `resolved`, `closed` | Verify the public reply; reopen the same case if needed. |

The panel can refresh the owner-scoped case and, only when the server permits,
jump to the reply form. It never sends Telegram/email, creates another case,
or performs a payment/provider/refund action.

## PWA and privacy

Support routes and `/api/v1/support/*` remain outside private service-worker
cache scope. Evidence links remain protected server downloads that re-check
case ownership, role and integrity.
