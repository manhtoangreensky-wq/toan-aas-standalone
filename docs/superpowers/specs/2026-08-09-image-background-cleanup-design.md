# Image Background Cleanup Design

## Goal

Add one bounded, truthful Web-native image operation that removes a contiguous
near-solid background from a signed owner's Asset Vault image and returns a
verified private transparent PNG.  It is an independent local utility, not an
AI segmentation claim or a substitute for the Bot's RemoveBG/Cutout workflow.

## Decision

Three implementation paths were considered:

1. Proxy the Bot's RemoveBG/Cutout path. Rejected: it would require the
   unavailable canonical bridge adapter, can reach paid providers and has Bot
   wallet/payment authority.
2. Ship a local semantic segmentation model. Rejected: no approved runtime,
   model provenance, resource envelope or output-validation contract exists.
3. Run a bounded edge-connected color cleanup locally. Chosen: Pillow can
   produce a real alpha PNG without a provider when the source has a simple
   background, while complex images remain honestly guarded or failed.

## User flow

1. The signed customer opens `/image/remove-background`.
2. The UI lists only active JPEG/PNG/WebP metadata owned by that customer in
   Asset Vault. It sends an opaque asset UUID, closed cleanup profile and
   idempotency key; it never sends bytes, paths, URLs, pixels or a Bot file ID.
3. The server copies and validates the source in the existing isolated Image
   Operations storage. It only flood-fills pixels connected to an image edge
   whose RGB distance remains within the selected conservative tolerance.
4. The server creates a fresh transparent PNG only after strict decode,
   dimension, alpha and SHA-256 validation. If no edge-connected pixels match,
   or the result cannot be validated, the operation fails without delivery.
5. History and download use the existing owner checks and signed-session
   private stream contract. The original Asset Vault object is never changed.

## Scope and boundaries

- New operation kind: `image_background_cleanup`.
- Closed profiles: `white_studio`, `light_neutral`, and `dark_neutral`; no
  arbitrary browser RGB/threshold/mask/path/provider input.
- The public name states that it cleans a plain background. It does not claim
  AI remove-background quality, subject detection, object deletion, image
  generation or provider delivery.
- The generic `/image/remove-background` bridge feature remains separate. It
  can stay guarded until a canonical provider adapter exists.
- No Bot source, Core Bridge code, provider credentials, wallet/PayOS tables,
  payment/webhook routes, or deployment/ENV configuration are modified.

## Architecture

`copyfast_image_operations.py` owns the request schema, closed profile
normalization, source inspection, bounded edge flood-fill, idempotency, audit,
private output record and download. `copyfast_db.py` adds a dedicated feature
flag accessor only. `copyfast_api.py` exposes the ready state without enabling
any bridge capability. `static/portal/portal.js` and `integration.js` add an
owner-scoped workspace, local history projection and CSRF/idempotent submit
behavior. The operation remains in the existing Image Operations table and
private storage root.

## Failure handling

- Disabled capability, missing Asset Vault, missing Pillow or unsafe source
  returns a safe guarded/validation response and creates no row/output.
- A source with no eligible edge-connected background returns a specific safe
  failure; the UI tells the user to use the canonical AI workflow when it is
  configured rather than pretending a cutout was made.
- Request replay returns the original owner-scoped receipt only for an identical
  fingerprint. A changed request under the same key returns conflict.
- Any source mutation, owner mismatch, storage tamper, stale output or invalid
  PNG keeps download unavailable.

## Acceptance evidence

- Targeted backend tests prove ownership, CSRF, idempotency, profile bounds,
  no-match failure, alpha output validation and tampered delivery failure.
- Portal contract tests prove no browser path/bytes/provider/Bot/wallet/payments
  and correct guarded state.
- The migration contract records this as an independent Web-native utility;
  raw `imgtool|*` callbacks remain fail-closed unless separately reviewed.
- The migration audit, focused tests, Python compile, JavaScript syntax check
  and `git diff --check` pass before PR/merge.
