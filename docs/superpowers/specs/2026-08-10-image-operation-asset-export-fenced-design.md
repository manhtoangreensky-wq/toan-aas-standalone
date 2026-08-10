# Fenced Image Operation → Asset Vault Export Design

## Decision

This document replaces the first export draft for `P1.WEBAPP.IMAGE.ASSET-EXPORT1`.
It keeps the narrow Web-only goal: a signed owner explicitly saves one verified
local Image Operation PNG to one independent private Asset Vault record.
It never creates a Bot/provider/job/payment/wallet/public-delivery surface.

Allowed kinds are exactly `image_resize`, `image_enhance`,
`image_background_cleanup`, and `image_brand_overlay`. Storyboard ZIP, AI
generation, Core Bridge, Telegram, Xu, PayOS, webhooks and public URLs remain
excluded.

## Effective capability and request

The only route is `POST /api/v1/image-operations/{operation_id}/export-to-asset-vault`.
It requires signed session, CSRF and this effective capability:

```text
WEBAPP_ASSET_VAULT_ENABLED
AND WEBAPP_IMAGE_OPERATIONS_ENABLED
AND WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED
```

The raw export flag defaults to false. The browser provides only a route UUID
and opaque `Idempotency-Key`; it never provides bytes, path/key/URL, filename,
hash, MIME, dimensions, project ID, provider/Bot/job/wallet/payment data.

## Fenced storage saga

Filesystem promotion and SQLite are not one atomic transaction. The contract
therefore guarantees one canonical committed Asset Vault row per operation,
not a false claim that a crash can never leave an unreferenced private file.
Every attempt owns a random destination key and a short fence lease. A stale
attempt cannot finalize, replace or delete a newer attempt.

Add `web_image_operation_asset_exports` with `operation_id` primary key,
`account_id`, unique nullable `asset_id`, `state` (`copying|completed`),
64-character request fingerprint, lease generation/token/expiry, reserved
bytes, unique pending storage key and timestamps. Its check invariant is:

```text
copying:  asset_id NULL, token/expiry/key present, reserved_bytes > 0
completed: asset_id present, token/expiry/key NULL, reserved_bytes = 0
```

Add `web_image_operation_asset_export_requests` keyed by
`(account_id, idempotency_key)`, mapping one opaque key to operation and
fingerprint. Same key on another operation conflicts; a different valid key
for the same operation returns the same asset. Never use generic
`web_idempotency.response_json`: that is a stale lifecycle snapshot.

All lease writes use this complete CAS predicate:

```sql
WHERE operation_id=? AND account_id=? AND state='copying'
  AND lease_generation=? AND lease_token=? AND lease_expires_at > ?
```

1. Reserve/replay in one short transaction: return a newly joined receipt if
   completed; return pending if live; otherwise CAS-reclaim with a new token
   and fresh random key. New reservation counts retained Vault bytes plus all
   other pending reservation bytes.
2. Outside SQLite, copy the verified source descriptor to private staging in
   bounded chunks, rehash it, strict-validate PNG, then exclusively promote an
   attempt-owned random object.
3. Finalize in one short transaction: prove lease/fingerprint/expiry,
   recheck quota, resolve Project as active-and-owned or `NULL`, insert Asset
   Vault metadata, complete relation, clear lease fields and append one
   redacted audit event. CAS loss rolls the asset insertion back.
4. A losing attempt cleans only its own staging/object key. Crash leftovers are
   later handled by normal orphan reconciliation after retention; this is
   explicit compensation, not a fake distributed transaction.

Regular Asset Vault upload quota checks include pending export reservations,
so upload cannot overcommit storage reserved for an export.

## Descriptor and PNG integrity

The Image Operations source opener accepts only DB-derived storage metadata.
It validates `outputs/<hex>.png` without resolving the final component; on
Railway/Linux it pins root plus `outputs/` with directory FDs and `O_NOFOLLOW`,
compares `lstat`/`fstat`, hashes and parses through the same open descriptor,
then keeps that descriptor open through copy. The fallback rejects symlinked
parent/final components and fails closed on identity change.

Kind derives PNG contract: resize/enhance/brand-overlay require RGB; cleanup
requires RGBA with at least one transparent pixel. Static PNG, exact dimensions,
complete decode, no EXIF, byte count and digest must all match. Destination
staging and final file are rehashed and strict-validated too.

Only source descriptor/hash/PNG failure marks the operation unavailable.
Quota, lease, destination write/fsync/validation or database failure releases
only the current lease and leaves the operation completed for retry.

## Truthful receipt and Portal

Every first response and replay reads a fresh owner-scoped join of export
relation and Asset Vault metadata/lifecycle. If the independent asset later
archives, restores or becomes unavailable, replay reports that current state
without making another copy. Lifecycle summary gets a redacted
`image_operation_export` reference count.

The Portal renders one secondary “Lưu vào Asset Vault” action only on a valid
completed/download-ready card in the exact four-kind allowlist when the
effective capability is published. It uses existing confirmation and in-memory
idempotency, one same-origin `api()` POST, then refreshes Image Operations and
Vault data. It never uses `fetch`, Blob, provider, bridge, Bot, wallet, PayOS
or browser byte/path/URL logic. The exact UUID POST family has one fixed early
rate-limit scope and all private response paths are `no-store, private`.

## Required evidence

- same/different keys return one current-lifecycle asset; same key on a second
  operation conflicts;
- a barrier test proves stale A cannot finalize/delete after B reclaims;
- reservation blocks concurrent export and normal upload without double count;
- symlink/directory swap/tamper/mode/alpha failures fail closed;
- destination failure keeps source operation completed; source integrity alone
  marks it unavailable;
- project archival during copy falls back to no Project; source/archive and
  asset lifecycle stay independent;
- public receipts/audits/UI omit path, key, hash, raw source filename,
  provider/Bot and wallet/payment data.
