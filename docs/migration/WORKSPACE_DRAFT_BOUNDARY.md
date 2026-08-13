# Workspace Drafts boundary

`/workspace` is a Web-owned authoring library. It prevents a customer from
losing an unfinished brief while moving between registered feature forms, but
it is deliberately not a second Bot job/asset/quote store.

## Web-only API

- `GET /api/v1/workspace/drafts?state=active|archived|all&feature_key=&q=&limit=&offset=`
- `GET /api/v1/workspace/drafts/{id}`
- `POST /api/v1/workspace/drafts`
- `PATCH /api/v1/workspace/drafts/{id}`
- `POST /api/v1/workspace/drafts/{id}/archive`

All reads and writes use the signed Web account. Writes require CSRF and an
idempotency key; an audit event stores only the opaque draft ID, feature key
and outcome. Every missing/foreign ID returns the same guarded response.

The list is a bounded, owner-scoped metadata projection. `state`, an exact
registered `feature_key`, and `q` (title/workflow metadata only) are optional;
the server clamps `limit` to 1–100 and `offset` to 0–10,000, returns one
look-ahead row, and exposes `has_more`, `next_offset`, `filters`,
`pagination`, and owner-only active/archive counts. It never selects, returns,
searches, or audits the saved scalar body from the list route. Full scalar
values are available only from the owner-scoped detail route when the customer
chooses **Tiếp tục brief**.

For compatibility, an omitted `state` keeps the original active-only list;
`include_archived=true` with omitted `state` means `state=all`. An explicit
`state` wins if both are supplied. The Portal sends filter/cursor data only to
the owner-scoped API while the current page is open: it does not put it into
the browser URL/history, `localStorage`, Telegram, an audit event, or a Bot
handoff. The Dashboard asks only for a small active metadata projection and
does not inherit a Workspace Library query.

## Stored and excluded data

The store accepts a bounded allowlist of scalar form values such as a brief,
prompt, platform, format, duration, language and planning choices. It rejects
nested objects, files, file names, paths, upload/staging IDs, Voice Vault
profile IDs, quote receipts, consent, identity/wallet/payment/provider/job/
output authority fields, secrets, card/OTP values, and manual-payment proof.
The content cap is 16 KB and there are at most 100 active drafts per account.

`GET /api/v1/catalog` declares `web_workspace_draft_supported` from the same
server-side feature allowlist. The Portal enables “Lưu bản nháp Web” only for
those exact workflows; history, assets and other read-only pages never expose
a button that would later be rejected by this API.

When a draft is resumed, the browser restores only the safe scalar values into
the exact registered workflow form. It never restores a file, canonical upload
reference, profile choice, estimate, quote, job, delivery, Xu amount or
payment state. The customer must pass the current form, upload, estimate and
Bot confirmation contracts again.

The same in-memory browser session remembers only the opaque draft UUID after
a resume, so “Cập nhật bản nháp Web” uses the owner-scoped `PATCH` endpoint
for that record. “Lưu thành bản mới” remains available for a deliberate copy.
This edit marker is never placed in `localStorage`, never enters feature input,
and cannot authorize a Bot operation.

After a create, update, or archive, the Portal invalidates the in-memory page
and re-reads the current owner-scoped list. It never inserts a returned record
optimistically into a filtered/history page, so ordering, state and pagination
remain server-authoritative.

## Explicit non-goals

Workspace Drafts never call the private bridge, create a Bot draft, invoke a
provider, calculate/charge Xu, create a PayOS order, publish content, or
claim an output is ready. It is usable by a signed account before Telegram
linking precisely because it owns no canonical Bot state.

## Project Studio handoff

An active Workspace Draft can become one explicit, Web-owned Studio snapshot
inside an active Project:

```text
POST /api/v1/projects/{project_id}/workspace-drafts/{draft_id}/attach
{
  "confirmed": true,
  "idempotency_key": "…"
}
```

The signed account must own both IDs; the request requires CSRF and a strict
JSON boolean `confirmed: true`. Missing confirmation, `false`, strings and
numbers are rejected before the route can write anything. The browser
checkbox and confirmation dialog are convenience/clarity controls only; the
server is the enforcement point.

Before writing, the Project boundary validates the stored row again. Its
feature key must still be an exact registered member of the same server-side
Workspace Draft allowlist used by intake and `/catalog`; a legacy, upgraded or
manually repaired row cannot introduce a new workflow. Forbidden authority
fields, files, credentials, Bearer/API-key material, OTP/CVV, plausible card
numbers and manual-payment proof are also rejected. This prevents the Studio
document and its immutable version history from becoming an alternate store
for sensitive or canonical data.

On success, one transaction creates exactly one active `brief` Studio
Document at revision 1, its immutable revision-1 row, a durable
`web_workspace_draft_handoffs` owner/project/draft receipt and one opaque
audit event. The draft itself stays active and unchanged. The unique
`(account_id, project_id, draft_id)` tuple is the durable duplicate guard:
even a retry with a new idempotency key returns the original receipt rather
than making a second document. Receipt links contain opaque IDs only; brief
content is never placed in a URL, audit detail or browser storage.

The handoff is not a Bot handoff. It does not submit a workflow, estimate a
price, make a provider request, create a job, mutate Xu/PayOS, attach a file
or claim media delivery. A later feature workflow must still satisfy its own
current form, upload, estimate, confirmation and canonical authority checks.
