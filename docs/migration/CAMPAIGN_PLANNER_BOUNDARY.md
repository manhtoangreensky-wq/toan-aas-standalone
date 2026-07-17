# Campaign Planner — Web-owned boundary

`/campaigns` is a signed-session Campaign Planner owned by the standalone Web
App. It gives each account a private board for a title, an HTTPS CTA
destination, platform, objective, local planning time and self-review status.
`/calendar` is a bounded, read-only month view and `/approvals` is a
self-review view over that same account-owned plan data; neither is a Bot
calendar or Admin approval replacement.

It is deliberately separate from both the legacy experimental `campaigns`
tables and the Bot campaign system:

| Web Campaign Planner | Telegram Bot / private adapter |
| --- | --- |
| Personal planning metadata | Canonical campaign identity/state |
| Local self-review (`draft → review → approved → scheduled`) | Staff approval, publishing queue and automation |
| Inert local calendar marker; explicit private Inbox intent only from Campaign detail | Reminder, channel scheduling and delivery execution |
| No analytics, revenue, CSV or provider calls | Canonical analytics/report commands and provider state |
| No Xu, PayOS or webhook writes | Wallet, PayOS and ledger authority |

The Web API is intentionally small:

- `GET /api/v1/campaigns`
- `GET /api/v1/campaigns/{id}`
- `GET /api/v1/campaign-calendar/window`
- `GET /api/v1/campaigns/{id}/schedule-intents`
- `POST /api/v1/campaigns`
- `PATCH /api/v1/campaigns/{id}`
- `POST /api/v1/campaigns/{id}/status`
- `POST /api/v1/campaigns/{id}/schedule-intents`
- `POST /api/v1/campaigns/{id}/schedule-intents/{intent_id}/cancel`
- `POST /api/v1/campaigns/{id}/schedule-intents/{intent_id}/reconfirm`

Every write requires the signed session, CSRF token and a bounded idempotency
key. Reads and updates are scoped with `account_id`; a plan ID alone cannot
reveal or modify another account's plan. HTTPS destinations are validated but
never fetched by the server. Audit events store only the opaque local plan ID
and a coarse status transition, never the plan title, destination URL,
affiliate data, Bot identity, provider data or payment data.

`web_campaign_plans.revision` is additive source-binding metadata, not a
canonical publication revision. An ordinary Campaign edit/status change fences
any active explicit private schedule intent in the same transaction. The owner
must reconfirm that future intent against the new revision; no time is silently
rescheduled and no Inbox delivery, Bot call, provider call or publish action is
created by that write.

The state label **approved** means “ready in this personal Web plan,” not a
staff/canonical publication approval. There is no `published` state,
calendar-triggered reminder, channel automation or publication scheduling. The
only narrow exception is an owner-confirmed schedule intent created from a
signed Campaign detail page; it can materialize one private Web Inbox record
under its separate contract, never a publish/delivery action. Any future
canonical campaign/publishing
adapter needs its own Bot-side contract, permission model, confirmation,
idempotency and audit review.

Legacy `/campaign.html` and `/campaign-app` bookmarks redirect to
`/campaigns`; old raw-`user_id` pages are not mounted.

`/campaigns/{id}` is a signed, owner-scoped Web detail view. It reads the
same local planning projection and can reuse the existing CSRF/idempotent
brief/self-review forms. It never falls back to a Bot campaign lookup when a
plan is absent or belongs to another Web account.

The Calendar window endpoint has its own narrow projection and one-month
database range; its precise response, browser stale-response fence and
explicit non-goals are recorded in
[`CAMPAIGN_CALENDAR_WINDOW_CONTRACT.md`](CAMPAIGN_CALENDAR_WINDOW_CONTRACT.md).
The explicit schedule-intent lifecycle, timezone/DST rules, Inbox dedupe and
privacy boundary are recorded separately in
[`CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md`](CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md).
