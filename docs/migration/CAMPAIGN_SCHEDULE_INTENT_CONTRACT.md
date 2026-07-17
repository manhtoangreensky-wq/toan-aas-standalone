# Campaign schedule intent — private Web Inbox contract

## Purpose and scope

An explicit Campaign schedule intent is a narrowly-scoped Web-native promise:
the signed owner can ask the verified Web notification scheduler to create one
private **Inbox record** at a future time. It is not a campaign publication,
channel schedule, calendar reminder, Bot command, provider job or external
notification.

The intent can only be created and managed on the signed Campaign detail page:

```text
/campaigns/{plan_id}
```

It does not exist on `/calendar`, `/approvals`, a list view, a URL parameter or
browser storage. In particular, `web_campaign_plans.scheduled_for` remains an
inert planning field. It never creates an intent or triggers a notification by
itself. Changing it is treated like changing other planning source metadata and
can require the owner to reconfirm an already-created intent.

## API and authorization

All paths below are under `/api/v1`, require a signed Web session, and scope
every lookup to the current `account_id` on the server:

```text
GET  /campaigns/{plan_id}/schedule-intents
POST /campaigns/{plan_id}/schedule-intents
POST /campaigns/{plan_id}/schedule-intents/{intent_id}/cancel
POST /campaigns/{plan_id}/schedule-intents/{intent_id}/reconfirm
```

- Reads return only the current owner's opaque schedule metadata.
- Writes require CSRF, server-resolved `user` or `admin` role, a confirmation
  boolean, an optimistic revision, and a bounded idempotency key.
- Before router/DB handling, Campaign detail/schedule reads use the fixed
  `campaign-schedule-read` per-IP family (120/minute) and POST/PATCH use
  `campaign-schedule-write` (40/minute). The bucket never includes a plan or
  intent UUID. A `429` returns the same no-delivery Web boundary; it does not
  replace signed-session, CSRF, ownership, revision or idempotency checks.
- A plan or intent from another account produces a guarded, non-disclosing
  response. Browser-supplied role, owner, source text, source digest and
  canonical/Bot identifier are never trusted.
- Create receives the plan only in the route. Its JSON body is exactly:

  ```json
  {
    "trigger_local_at": "2026-07-16T14:30:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "expected_plan_revision": 3,
    "opt_in": true,
    "confirm": true,
    "idempotency_key": "opaque-client-key"
  }
  ```

  Extra fields are rejected. Cancel requires `expected_revision`, `confirm`
  and `idempotency_key`; reconfirm also requires
  `expected_plan_revision`.

Every response carries a Web-only boundary: `source_content_copied=false`,
`scheduled_for_is_inert=true`, `delivery=in_app_record_only`, and false flags
for Bot, bridge, provider, publish, wallet, payment, job and external
notification effects. The browser treats a response missing that boundary as
guarded rather than rendering a writable schedule UI.

## Time and source binding

The owner submits a `datetime-local` wall time and an IANA zone. The server:

- accepts only `YYYY-MM-DDTHH:MM[:SS]` with a named IANA zone (or `UTC`);
- rejects unsupported zones, nonexistent DST wall times and ambiguous DST
  folds instead of guessing;
- normalizes and stores both the reviewed local wall time/zone and one UTC
  trigger;
- requires at least one minute of lead time and at most 366 days ahead.

The source is bound server-side to the plan's additive `revision` and a digest
of the current Web-owned planning fields: title, HTTPS destination, platform,
objective, inert `scheduled_for`, self-review status and review note. The
digest is never returned to the browser or copied into Inbox content.

## Storage, limits and state machine

`web_campaign_schedule_intents` is an additive Web-owned table. Its durable
columns are opaque intent/account/plan IDs, source revision/digest, local
trigger, zone, normalized UTC trigger, state/revision, actor and timestamps.
It intentionally has no title, CTA URL, review-note copy, source JSON,
canonical campaign ID, provider handle, payment value or output payload.

Limits are deliberately small: 200 historical intents/account, 50 active
intents/account and 20 active intents/plan. A partial unique index prevents
two active intents for the same account, plan, source revision and UTC trigger.

```text
active    -> dispatched   verified due source materializes exactly one Inbox item
active    -> guarded      Campaign source/revision/digest no longer matches
guarded   -> active       owner explicitly reconfirms the same still-future time
active    -> cancelled    owner cancels before materialization
guarded   -> cancelled    owner cancels instead of reconfirming
```

`dispatched` and `cancelled` are terminal. Reconfirm never shifts time or
creates a replacement intent. If the stored time is already expired or its
zone/UTC relationship no longer validates, the owner must make a new explicit
choice instead.

Normal Campaign PATCH/status writes increment the plan revision and fence
active intents to `guarded` in the **same local transaction**. This makes a
future intent actionable immediately: the owner can reconfirm it before its
time passes. The notification tick independently rechecks the source digest to
defend against an out-of-band data change; it only guards the intent and never
rewrites the plan, Calendar or review state.

## Inbox materialization

The existing authenticated Notification Center tick is the only scheduler. It
does not introduce a second Cron, secret, provider or delivery adapter. Once a
due `active` intent still has a matching owner/source revision/digest, the tick
creates at most one owner-scoped Inbox record:

```text
kind=campaign_schedule_due
source_kind=campaign_schedule_intent
source_id=<opaque intent UUID>
source_revision=<intent revision>
occurrence_at=<normalized UTC trigger>
delivery=in_app_record_only
```

Dedupe binds account, intent ID, revision and occurrence time. A retry, lease
handoff or replay cannot generate a second record. The Inbox record contains no
Campaign title, destination, review note or source snapshot. Its Portal link
goes to the signed Campaign list, never reconstructs a source-detail URL from
the scheduler receipt.

The tick cannot create Telegram, email, SMS, web push, Bot or bridge activity;
call a provider; publish; mutate wallet/Xu/PayOS; create/retry a job; touch an
asset; or deploy/restart infrastructure.

## Privacy, PWA and verification

Campaign detail, schedule APIs, Calendar and Approvals are explicit private
PWA paths. The service worker cache has a fixed public shell allow-list and
never caches their navigation responses, schedule metadata, Inbox records or
authenticated API responses.

Focused verification covers signed ownership/CSRF/idempotency, opaque schema,
inert `scheduled_for`, timezone/DST rejection, one-record dedupe, immediate
source-change guard, future-time reconfirmation, Inbox rendering, PWA private
path handling and import safety. It uses local mocked tick state only; it does
not call Bot, Telegram, bridge, provider, PayOS, wallet, jobs or a live Cron.
