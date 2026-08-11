# Image Operation Export to Content Handoff Design

## Goal

Let a signed owner deliberately continue from one verified, completed Web-native
Image Operation PNG into a new Content Handoff draft with the resulting active
Asset Vault item preselected. The continuation is navigation only: it does not
create a Content Handoff record, job, provider request, wallet entry, payment,
or external delivery.

## Selected approach

Keep the existing **Lưu vào Asset Vault** action unchanged and add a distinct
**Lưu & chuẩn bị bàn giao** action on completed PNG operation cards only when
both `image-operation-export-to-asset-vault` and `content-handoff-create`
capabilities are true. Both controls use the same existing fenced export POST.
The continuation can navigate only after its response has all of the following:

- envelope status `completed`;
- a syntactically valid opaque Asset Vault UUID; and
- an Asset Vault receipt state of `active`.

```text
Image Operation card
  -> explicit export-and-prepare action
  -> existing owner-scoped Image Operation export POST
  -> completed + active Asset Vault receipt
  -> /content/handoffs/new?asset_id=<opaque UUID>
  -> existing owner-scoped handoff form selects active Vault asset
  -> existing explicit Content Handoff create action revalidates ownership
```

The query value remains an untrusted convenience hint. The already-existing
Content Handoff renderer uses it only for a new record and only if it matches
the active Asset Vault projection for the current signed account.

## Rejected alternatives

- **Auto-create a Content Handoff record after image export:** rejected because
  a valid image artifact is not consent to create a coordination record.
- **Navigate from `archived` or `unavailable` receipts:** rejected because the
  target form must not select a non-active asset.
- **Add an image-specific handoff endpoint or copy bytes in the browser:**
  rejected because the existing export endpoint owns source validation, fenced
  staging, output integrity, quota, and Asset Vault lifecycle truth.
- **Call image providers or infer price from the provisional catalog:**
  rejected because this Web-native continuation has no provider, bridge,
  wallet, payment, or canonical-cost authority.

## Security and lifecycle boundary

- The browser sends only the Image Operation UUID to the existing same-origin
  export endpoint, using the existing CSRF/session and idempotency safeguards.
- Pending, guarded, malformed, archived, or unavailable receipts never form a
  Content Handoff URL.
- The URL contains only one opaque Asset Vault UUID: no file name, byte stream,
  path, digest, provider handle, Bot state, wallet, or payment data.
- The current Content Handoff create endpoint remains the sole writer and
  transactionally rechecks active ownership of referenced assets.
- This slice changes no server route, schema, flag, service worker policy, Bot,
  core bridge, provider, pricing, wallet, PayOS, webhook, or environment value.

## Acceptance evidence

1. Image cards render the continuation only with both existing capabilities
   and a completed, download-ready PNG.
2. The portal reuses the export endpoint and idempotency semantics, but never
   posts to a Content Handoff write endpoint.
3. Only `completed + active` receipts navigate; `queued`, `processing`,
   `guarded`, `archived`, and `unavailable` remain truthful in place.
4. The existing Content Handoff active-owner prefill comparator stays green.
5. The final diff is limited to portal JavaScript, focused contracts, and this
   design/plan; protected backend, Bot, payment, provider, PWA, and ENV paths
   remain unchanged.
