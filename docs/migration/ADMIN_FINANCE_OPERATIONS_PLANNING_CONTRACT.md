# Admin Finance Operations Planning contract

`/admin/finance/planning` is a private, Web-native Admin ERP workspace for
internal operating-cost planning.  It is deliberately a planning surface, not
a second financial system.

## Authority boundary

The standalone Web App owns only these additive records:

- monthly budget plans by a closed internal category;
- prospective cost plans and their internal review lifecycle; and
- planning event/audit metadata.

It must **not** read or write Bot/canonical finance tables, Xu, wallet,
top-ups, revenue, refunds, invoices, tax calculations, accounting exports,
PayOS, payment/webhook state, provider state, jobs or delivery.  It accepts no
manual payment proof, QR, TXID, bill, bank-account data, secret or credential.
It never calls the Core Bridge, Bot, a provider, PayOS or a notification
adapter.

Every API envelope includes a machine-readable boundary which keeps the above
claims observable (`canonical_finance_read`, `canonical_finance_write`,
`bot_called`, `bridge_called`, `provider_called`, `wallet_mutated`,
`payment_started`, `payment_finalized`, `payos_webhook_created`,
`refund_created`, `ledger_changed`, `tax_calculated`, `report_exported` and
`notification_sent` are all `false`).

## Access and feature gates

The HTML route and all API reads require the signed Web-local `admin` role.
Writes additionally require the existing CSRF guard.  A browser-provided role,
Telegram ID or canonical Bot-admin hint never grants this workspace.

Both flags must be enabled:

```text
WEBAPP_ADMIN_ERP_ENABLED=true
WEBAPP_FINANCE_PLANNING_ENABLED=true
```

The second flag controls only this Web-owned planning module; it never enables
canonical finance reads/writes, Xu/PayOS, manual payment evidence, tax/export
or provider work.  When either flag is off, the API fails closed with `503` and
the Portal presents the module as guarded rather than showing cached plans.

## Data model and lifecycle

All tables use the separate `web_finance_planning_*` namespace:

- `web_finance_planning_budgets` has one non-archived budget per
  `(period, category)`.
- `web_finance_planning_costs` holds a prospective, internal cost plan.
- `web_finance_planning_events` is an append-only planning lifecycle trail.

`period` is a valid `YYYY-MM`; a cost's `planned_for` date must fall in that
period.  Amounts are positive integer VND values, capped server-side.  The
only categories are `infrastructure`, `provider_runtime`, `software`,
`marketing`, `operations` and `other`.

Budget lifecycle:

```text
active -> archived -> active
```

Archiving preserves the original row and audit trail.  Restoring is rejected
when another active budget already occupies the same `(period, category)`.

Cost-plan lifecycle:

```text
draft -> review -> approved -> archived
review -> draft
archived -> draft
draft -> archived
review -> archived
```

The server owns this state graph and compare-and-set `revision`; the browser
must send the last observed revision and never infer a transition locally.
`approved` means only “approved for internal planning”.  It does not authorize
a purchase, charge, provider request, payment, payout or refund.

## API contract

Prefix: `/api/v1/admin/finance-planning`

| Method | Route | Role | Purpose |
| --- | --- | --- | --- |
| `GET` | `/policy` | signed admin | closed vocabulary, lifecycle and boundary |
| `GET` | `/summary?period=` | signed admin | aggregate planning totals only |
| `GET` | `/budgets?period=&state=&limit=&offset=` | signed admin | bounded Web-owned budgets |
| `GET` | `/cost-plans?period=&state=&category=&limit=&offset=` | signed admin | bounded Web-owned cost plans |
| `POST` | `/budgets` | signed admin + CSRF | create a confirmed budget plan |
| `POST` | `/budgets/{uuid}/state` | signed admin + CSRF | archive or restore a budget with revision check |
| `POST` | `/cost-plans` | signed admin + CSRF | create a confirmed cost plan in `draft` |
| `POST` | `/cost-plans/{uuid}/state` | signed admin + CSRF | transition a cost plan with revision check |

Write bodies are strict and reject unknown keys.  They require an explicit
confirmation (`confirm_budget`, `confirm_plan` or `confirm_change`) and a
validated idempotency key.  Idempotency is scoped by the signed account and
operation, fingerprints the semantic request, and retains an opaque replay
receipt for 24 hours.  Reusing a key for a different request fails with `409`;
the replay receipt deliberately omits amount and planning text.

All records and planning events have server-issued UUIDs, timestamps, revision
and server-side audit entries.  The Portal must use normal CSRF-aware API
calls, confirmation UI and a newly generated idempotency key for each intended
write.  It must rehydrate after a successful mutation and clear stale state on
session, route or feature-gate changes.

## Portal and PWA rules

The Portal route is a distinct `admin-finance-planning` layout.  It exposes
only: period totals, budget entry, prospective cost-plan entry, bounded lists,
server-allowed budget/cost lifecycle controls and a refresh action.  It must
surface the boundary prominently so a finance plan cannot be mistaken for a
payment or ledger.

The route is excluded from the public PWA shell and must not persist plans,
IDs, input drafts, CSRF values, receipts or credentials in browser storage.
No UI control may offer PayOS, Xu, wallet, top-up, refund, payment evidence,
tax/export, Bot or provider action.

## Operational interpretation

This module is useful internal planning metadata only.  A team must complete
any real procurement, payment, refund, accounting or compliance process in
the separately governed canonical system.  This contract makes no claim that
the Web App can execute those processes.
