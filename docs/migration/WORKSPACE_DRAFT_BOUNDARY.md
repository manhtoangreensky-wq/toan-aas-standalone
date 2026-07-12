# Workspace Drafts boundary

`/workspace` is a Web-owned authoring library. It prevents a customer from
losing an unfinished brief while moving between registered feature forms, but
it is deliberately not a second Bot job/asset/quote store.

## Web-only API

- `GET /api/v1/workspace/drafts`
- `GET /api/v1/workspace/drafts/{id}`
- `POST /api/v1/workspace/drafts`
- `PATCH /api/v1/workspace/drafts/{id}`
- `POST /api/v1/workspace/drafts/{id}/archive`

All reads and writes use the signed Web account. Writes require CSRF and an
idempotency key; an audit event stores only the opaque draft ID, feature key
and outcome. Every missing/foreign ID returns the same guarded response.

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

## Explicit non-goals

Workspace Drafts never call the private bridge, create a Bot draft, invoke a
provider, calculate/charge Xu, create a PayOS order, publish content, or
claim an output is ready. It is usable by a signed account before Telegram
linking precisely because it owns no canonical Bot state.
