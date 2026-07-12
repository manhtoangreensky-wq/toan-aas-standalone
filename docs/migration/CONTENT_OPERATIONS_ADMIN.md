# Content Operations Admin Navigation Contract

The Admin ERP directory exposes dedicated, role-gated navigation surfaces for
the operations mapped from Telegram Bot commands:

- `Campaign Center` — `/admin/campaigns`
- `Content Calendar` — `/admin/calendar`
- `Approval Queue` — `/admin/approvals`
- `Publishing & Channels` — `/admin/publishing`
- `Analytics` — `/admin/analytics`

These pages are discoverable Web routes, not a claim that their Bot data or
write adapters are available. Each still requires a signed Web session and a
fresh canonical Bot admin-role check before the page may read data.

Until the private Bot bridge ships a module-specific read/write contract, the
pages remain read-only/guarded and show the canonical adapter message. They do
not create campaigns, edit calendars, approve jobs, publish content, invoke a
provider, calculate analytics/revenue, export data, or schedule automation
from the browser.

Legacy Bot command aliases are grouped under the relevant visible module for
navigation only. Any future write must meet the CSRF, confirmation,
idempotency, permission and audit requirements in
[`ADMIN_WRITE_CONTRACT.md`](ADMIN_WRITE_CONTRACT.md).

The customer-facing [`Campaign Planner`](CAMPAIGN_PLANNER_BOUNDARY.md) at
`/campaigns` is separate: it stores only account-owned Web planning metadata
and does not turn these admin/Bot read-only surfaces into a publishing or
analytics adapter.
