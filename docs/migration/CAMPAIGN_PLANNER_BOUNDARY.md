# Campaign Planner — Web-owned boundary

`/campaigns` is a signed-session Campaign Planner owned by the standalone Web
App. It gives each account a private board for a title, an HTTPS CTA
destination, platform, objective, local planning time and self-review status.
`/calendar` and `/approvals` are read/write views over that same account-owned
plan data; they are not Bot calendar or Admin approval replacements.

It is deliberately separate from both the legacy experimental `campaigns`
tables and the Bot campaign system:

| Web Campaign Planner | Telegram Bot / private adapter |
| --- | --- |
| Personal planning metadata | Canonical campaign identity/state |
| Local self-review (`draft → review → approved → scheduled`) | Staff approval, publishing queue and automation |
| Local calendar marker only | Reminder, channel scheduling and delivery execution |
| No analytics, revenue, CSV or provider calls | Canonical analytics/report commands and provider state |
| No Xu, PayOS or webhook writes | Wallet, PayOS and ledger authority |

The Web API is intentionally small:

- `GET /api/v1/campaigns`
- `GET /api/v1/campaigns/{id}`
- `POST /api/v1/campaigns`
- `PATCH /api/v1/campaigns/{id}`
- `POST /api/v1/campaigns/{id}/status`

Every write requires the signed session, CSRF token and a bounded idempotency
key. Reads and updates are scoped with `account_id`; a plan ID alone cannot
reveal or modify another account's plan. HTTPS destinations are validated but
never fetched by the server. Audit events store only the opaque local plan ID
and a coarse status transition, never the plan title, destination URL,
affiliate data, Bot identity, provider data or payment data.

The state label **approved** means “ready in this personal Web plan,” not a
staff/canonical publication approval. There is no `published` state, calendar
reminder or channel automation. Any future canonical campaign/publishing
adapter needs its own Bot-side contract, permission model, confirmation,
idempotency and audit review.

Legacy `/campaign.html` and `/campaign-app` bookmarks redirect to
`/campaigns`; old raw-`user_id` pages are not mounted.

`/campaigns/{id}` is a signed, owner-scoped Web detail view. It reads the
same local planning projection and can reuse the existing CSRF/idempotent
brief/self-review forms. It never falls back to a Bot campaign lookup when a
plan is absent or belongs to another Web account.
