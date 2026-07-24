# Audio Collection → Audio Asset Operations Handoff Contract

## Purpose

This is a small Web-native handoff from an **active** Media Workspace collection
attachment to the existing private `/audio/assets` utility. It removes repeated
source selection when a customer intentionally chooses a verified audio
reference, without importing a Bot music/SFX state machine into the browser.

It is not an Audio Hub, player, catalog, provider integration, job queue,
asset-import workflow, output delivery surface, or a replacement for Bot
callbacks.

## Entry and target

- Source route: `/media-workspace/{collection_id}`.
- Target route: `/audio/assets`.
- The control is shown only for an attached item returned by the signed
  collection-detail read when all of the following remain true:
  - collection is `active`;
  - item and its `asset_id` are valid UUIDs and still match;
  - Asset Vault projection is `active`, private and download-available;
  - source is an allowlisted MP3, WAV, M4A or OGG pair within the existing
    25 MiB Audio Asset Operations limit.
- The customer must explicitly press **Mở Audio Operations**. There is no
  implicit navigation, submit, inspect, convert, normalize, job or output.

## Browser boundary

1. The click handler checks the route, collection ID, item ID and the current
   signed-detail projection as a preflight. A forged, stale, detached,
   inactive, foreign or mismatched item has no usable handoff source.
2. Before changing routes, it performs a fresh no-store, signed,
   owner-scoped collection-detail read and validates the exact active item,
   attachment delivery and typed Asset Vault projection a second time. A
   reference archived, detached or changed after rendering is rejected before
   any UUID is carried to Audio Asset Operations.
3. It clears an earlier Audio Asset Operations projection, changes only the
   local route to `/audio/assets`, and calls the existing owner-scoped typed
   audio hydration with one opaque Asset Vault UUID.
4. The UUID exists only inside that immediate JavaScript call. It is never
   written to a URL/query, `localStorage`, `sessionStorage`, form draft,
   cookie, analytics event, Telegram message, Bot callback, provider request,
   payment, wallet/Xu record or job payload.
5. Existing hydration selects the source only if its fresh
   `state=active&reference_kind=audio` response returns the exact UUID. If it
   no longer appears, the selection is cleared and the customer must choose a
   source again. The Web App never falls back to a generic Asset list, a stale
   DOM object, path, URL, cache entry or media preview.
6. A current Audio Asset Operations view has its own epoch. A late confirmed
   operation receipt from an older view cannot overwrite a newer handoff,
   source-page selection, route or signed-session bootstrap.
7. Direct `/audio/assets` navigation remains unchanged: it has no handoff
   source and starts with the normal private typed picker.

## Server authority remains unchanged

This handoff adds no API and no server-side write. The existing
`/api/v1/audio-asset-operations/{inspect,convert,normalize}` boundary remains
the sole authority for every operation:

- signed active account and CSRF are required for writes;
- source lookup requires the same account, `active` lifecycle, exact
  extension/MIME pair, bounded size, sealed storage key, digest and lifecycle
  revision;
- claim, source copy and completion each revalidate the immutable source
  snapshot; an archived/replaced/revised source fails as `AUDIO_SOURCE_CHANGED`;
- only a verified completed transform exposes a private attachment; inspect
  never creates an output.

No Bot/Core Bridge, provider, Key4U, PayOS, wallet/Xu, Telegram identity,
catalog, preview/player, browser FFmpeg, upload, raw file path, public URL,
or output import into Asset Vault is introduced by this handoff.

## Focused acceptance checks

- A valid active collection reference can open `/audio/assets` but does not
  automatically submit an operation.
- An invalid collection/item ID, stale detail, collection/item archived or
  detached after rendering, inactive asset or missing typed source cannot
  preselect anything.
- A source absent from the newly hydrated owner-scoped typed list is cleared;
  no stale selection is retained.
- A confirmed older operation receipt cannot restore its old selected source
  after the customer has initiated a newer handoff or source-page change.
- Direct `/audio/assets` behavior is unchanged and no handoff data survives a
  later navigation or signed-session bootstrap.
- The existing audio operation source-race test proves that a lifecycle change
  after claim cannot finish with a successful output.
