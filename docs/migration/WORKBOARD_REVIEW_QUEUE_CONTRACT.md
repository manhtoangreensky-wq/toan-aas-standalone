# Web-native Workboard & Review Queue

## Purpose and authority boundary

`/workboard` is a private Kanban and self-review workspace owned by a signed
TOAN AAS Web account. It gives a customer one place to coordinate the work
they already own in the Web App without turning a browser board into a
Telegram Bot, provider, publishing or billing controller.

| Surface | Owner | It never does |
| --- | --- | --- |
| Workboard item and checklist | Signed Web account | Call Bot, Core Bridge, provider, social platform, wallet/Xu, PayOS, jobs, publish or notification APIs. |
| Reference | Same signed Web account | Fetch a URL, read a file/blob, expose another account's content or use an unverified browser-supplied ID. |
| `review` / `done` state | Signed Web account | Assert an admin approval, engine success, job delivery, publication, payment or notification delivery. |
| Telegram Bot work queue | Frozen Bot baseline | Appear automatically in this board or receive a Web item state. |

The module is intentionally Web-native. It owns tables prefixed
`web_workboard_`; it neither reads nor migrates Bot task/job tables.

## Lifecycle

```text
backlog -> planned -> in_progress -> review -> done
                 \-> archived
done -> planned | archived
archived -> backlog | planned | in_progress | review | done
```

State changes are private self-management choices. An archived item is kept
for history and may be restored through an immutable prior snapshot; the
system never deletes history in place. Completing a checklist or moving a
card does not create a reminder, external automation, message or publish
queue.

## References

The client may submit only an allowlisted opaque UUID reference. The server
rechecks both identifier format and ownership in the same account before a
write succeeds:

| `ref_type` | Web-owned source |
| --- | --- |
| `project` | Project Center project |
| `campaign` | Campaign Planner plan |
| `analytics` | Analytics Workspace report |
| `note` | Memory Center note |
| `draft` | Web Workspace draft |

References contain no source title, text, URL, asset path, file/blob,
Telegram identity, provider handle, job, wallet, payment, output or delivery
data. A Workboard cannot receive arbitrary links or use a reference as a
server-side fetch instruction.

## API

All API responses use the normal envelope. Every item query is constrained by
the signed account ID; a foreign or missing UUID produces the same guarded
not-found response.

```text
GET   /api/v1/workboard/policy
GET   /api/v1/workboard/summary
GET   /api/v1/workboard/items?state=&priority=&ref_type=&ref_id=&q=&include_archived=&limit=&offset=
POST  /api/v1/workboard/items
GET   /api/v1/workboard/items/{item_id}
PATCH /api/v1/workboard/items/{item_id}
POST  /api/v1/workboard/items/{item_id}/state
GET   /api/v1/workboard/items/{item_id}/versions
POST  /api/v1/workboard/items/{item_id}/restore/{revision}
POST  /api/v1/workboard/items/{item_id}/checklist
PATCH /api/v1/workboard/items/{item_id}/checklist/{checklist_id}
GET   /api/v1/workboard/items/{item_id}/events
GET   /api/v1/workboard/events
```

Writes require a signed session, CSRF token, bounded idempotency key and
optimistic `expected_revision`. Checklist updates additionally send the
checklist revision. Idempotency records return redacted receipts, never the
private title, description or checklist body. The server keeps append-only
item and checklist version snapshots plus audit/event records that expose
only opaque IDs, transition/action and revision metadata.

## Input and privacy controls

- Title, description, checklist text and search text have strict length and
  control-character limits. URLs/paths, HTML/script tags, secrets, bearer
  tokens, passwords, OTP/CVV, card-shaped values, bank/payment/manual-topup
  markers and raw Telegram/provider handles are refused.
- All list limits, reference counts, checklist counts and event/version
  history are bounded. No file upload, import, export or background worker is
  available.
- The List view exposes only the server's owner-scoped `q`, `state` and
  `priority` filters plus bounded pagination. Filter text is held only in the
  current Web view, never in a URL, browser storage, Bot state or a
  background search index; Kanban always reloads its unfiltered active board.
- Every private API response is `no-store, private`; the service worker must
  not cache `/workboard`, `/workboard/*` or `/api/v1/workboard/*`.
- The feature flag `WEBAPP_WORKBOARD_ENABLED` defaults to `true`. Setting it
  false returns a fail-closed maintenance response without a Bot fallback.

## Non-goals and future adapters

Workboard is not a job center, staff approval system, calendar publisher,
team notification system, AI planner, social analytics integration or task
execution engine. Future collaboration, notification or canonical execution
requires its own consent, identity, role, delivery, retry, idempotency and
audit contract; it cannot be enabled by a Workboard checkbox.

## Verification

Focused tests cover signed-session/CSRF gates, idempotency collision, owner
isolation, reference allowlist ownership, revision conflicts, state and
checklist history, sensitive-input rejection, disabled mode, body limits,
no-network/Bot/payment imports, portal capability boundary and service-worker
private-cache exclusion. They do not claim a live Bot, provider, PayOS or
notification flow.
