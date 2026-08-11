# Document Export to Content Handoff Prefill Design

## Goal

Let a signed owner deliberately continue from one verified Document Operation
artifact into a new Content Handoff draft with that active Asset Vault item
preselected.  The continuation is navigation only: it must not create a
handoff, job, delivery, provider request, wallet entry, payment, or external
action.

## Selected approach

Keep the existing **Lưu vào Asset Vault** control unchanged and add a distinct
**Lưu & chuẩn bị bàn giao** control only when both existing capabilities are
enabled.  Both controls use the same fenced server-side export route.  The new
control navigates only after that route returns a `completed` receipt with a
valid Asset Vault ID in `active` state:

```text
Document Operation card
  -> explicit export-and-prepare action
  -> existing owner-scoped export POST
  -> completed + active Asset Vault receipt
  -> /content/handoffs/new?asset_id=<opaque UUID>
  -> existing handoff form selects the active owner-scoped asset
  -> existing create action and server ownership check
```

The Content Handoff form treats `asset_id` as an untrusted convenience hint. It
uses it only for a new record, only when the opaque UUID is present in the
already owner-scoped active Vault projection, and otherwise leaves the selector
empty.  `copyfast_content_handoff._references_owned` remains the final
authority and is not changed.

## Rejected alternatives

- **Automatic record creation after export:** rejected because a completed
  Artifact is not consent to create a coordination record, and it would blur
  audit intent and idempotency boundaries.
- **Blind query-string prefill:** rejected because a browser-provided UUID
  could reference a missing, archived, foreign, or stale asset.
- **Browser file copy or a new API:** rejected because the existing export
  fence owns source validation, staging, integrity validation, and receipt
  truth.

## Security and lifecycle boundary

- The browser posts only the existing Document Operation UUID to the same
  origin export route with the existing CSRF and idempotency safeguards.
- Pending, guarded, malformed, archived, or unavailable receipts never
  navigate to a prefilled draft.
- The resulting URL contains only an opaque UUID; no filename, storage key,
  digest, path, source bytes, recipient, provider, Bot, wallet, or payment data
  is transferred.
- The ordinary Content Handoff create action remains the only writer.  Its
  existing owner/state checks revalidate all `asset_ids` transactionally.
- No server route, schema, feature flag, service worker cache rule, provider,
  payment, or Bot code changes in this slice.

## Test contract

Focused portal contracts must prove that:

1. the new continuation control is opt-in and gated by the two existing
   capabilities;
2. only an active completed receipt can form the handoff navigation URL;
3. query prefill selects only an active Asset Vault item available in the
   current owner projection;
4. the continuation action still performs just the existing opaque export POST
   and never invokes a Content Handoff write; and
5. existing Content Handoff tests keep the server-side active-owner comparator
   green.
