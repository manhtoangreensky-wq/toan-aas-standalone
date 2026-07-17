# Campaign Calendar window — Web-native contract

`/calendar` is a signed, **read-only** monthly view for the standalone Web
account. It is intentionally narrower than Campaign Planner: the page asks
for one owner-scoped month window at a time and displays only the planning
metadata required to render a calendar and agenda.

## Route and input contract

```text
GET /api/v1/campaign-calendar/window?month=YYYY-MM&status=...&platform=...
```

- `month` is required and must be `2000-01` through `2100-12`.
- `status` is `all`, `draft`, `review`, `approved`, `scheduled`, or
  `archived`.
- `platform` is `all`, `facebook`, `instagram`, `tiktok`, `youtube`,
  `website`, or `other`.
- Invalid input is rejected with the normal sanitized `422` request error;
  the browser does not widen the request or substitute a history query.
- The database predicate always contains `account_id = current account`, a
  non-empty local `scheduled_for`, and the exact half-open selected-month
  range. Optional filters are additional predicates, never client-side
  ownership rules.

The response uses the normal envelope with status `read_only` and contains:

```json
{
  "month": "2026-07",
  "filters": { "status": "all", "platform": "all" },
  "items": [
    {
      "id": "uuid",
      "title": "Kế hoạch Web",
      "platform": "tiktok",
      "objective": "traffic",
      "scheduled_for": "2026-07-16T09:30",
      "approval_status": "draft",
      "updated_at": "2026-07-15T12:00"
    }
  ],
  "summary": { "total": 1, "returned": 1, "has_more": false, "limit": 200 }
}
```

The server cap is 200 items. `has_more` makes truncation visible; the Web UI
does not silently fetch all planning history. The projection deliberately
excludes CTA URLs, self-review notes, account identifiers, canonical campaign
identifiers, provider data, jobs, output locations and payment data.

## Browser behavior

The Calendar maintains selected month and filters only in its current signed
runtime state. They are not placed in the URL, persisted in browser storage,
or inferred from a Bot/Telegram payload. A dedicated request epoch, signed
session epoch, route check and selected-window key discard a stale response
after navigation, account change, filter change or a Campaign Planner write.

The UI provides month navigation, status/platform filters, a bounded month
grid and chronological agenda. Opening an item returns to that plan's
owner-scoped Campaign Planner detail page. Calendar itself has no write,
confirmation, CSRF mutation, publish or automation action.

## Boundaries that remain intentionally absent

This contract is not a Bot calendar, Admin Calendar, publishing queue or
workflow engine. It does not read or modify:

- Telegram/Bot campaign state, Bot identity, reminders or notifications;
- canonical social schedules, channel connections, publish/delivery state or
  analytics;
- providers, jobs, files/assets, output validation or worker state;
- Xu ledger, wallet, PayOS, payment signatures, webhooks or refunds; or
- `/admin/calendar` and any staff ERP calendar surface.

`scheduled_for` remains a local, inert planning timestamp. It becomes neither
a reminder nor a publication schedule merely by appearing in this view.

An owner may separately create a private schedule intent from the signed
Campaign detail page. Calendar does not list, create, cancel or reconfirm that
intent, and never infers it from `scheduled_for`. Editing a plan can fence an
already-created intent for owner reconfirmation because its source binding
changed; that still does not create a reminder, delivery or publish action.
See [`CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md`](CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md).

## Verification scope

Focused tests cover route ordering, exact-month parsing, owner predicate,
narrow response projection, filter rejection, response cap/cache policy,
browser stale-response fencing, no generic Campaign Planner fallback, and the
Calendar renderer's no-network/no-browser-storage boundary. They do not run a
Bot, provider, payment flow, Telegram link, admin calendar or deployment.
