# Music & SFX Library — Web-native contract

## Purpose

`GET /api/v1/media-workspace/library-items` is the signed Web App's private,
metadata-only listing for the customer-facing Music Library (`/music/library`
and legacy alias `/music-library`) and SFX Library (`/music/sfx-library`). It
replaces the former generic bridge/asset-list presentation with a focused,
account-owned view of audio references that the customer has actively attached
to a Web Media Workspace collection.

The listing is not an audio catalogue, player, delivery centre or generation
workflow. It makes no claim that a track is licensed, cleared, approved,
available for release, playable or downloadable.

## Signed owner read model

- A normal signed Web session is required. The account ID is resolved
  server-side; a collection UUID, asset UUID, URL parameter or browser state
  never grants access on its own.
- `role` is required and is exactly one of `music` or `sfx`. `reference` is
  deliberately not a library view. `q`, `limit` and `offset` are bounded
  read-only filters/pagination controls.
- The source is only the intersection of the signed account's active
  `web_media_items`, active `web_media_collections` and active audio
  `web_asset_files`. A detached item, an archived collection, an inactive
  asset or another account's attachment is absent from the result.
- The response provides a small display projection only: collection UUID and
  title, role, an explicit custom reference title (or neutral `Audio reference`
  when none was set), bounded tags, favourite flag, optional
  user-declared duration, and timestamps needed for a stable library view.
  It never exposes an item/asset UUID, storage key, digest, original filename,
  content path, signed URL, download URL, bytes, MIME type, attribution,
  license note, creative brief or provider/cache identifier.
- The endpoint uses the ordinary Web API envelope with `status: "read_only"`.
  `data` contains exactly the metadata listing contract:

  ```json
  {
    "items": ["safe library item metadata"],
    "filters": {"role": "music|sfx", "q": "normalized query"},
    "pagination": {
      "limit": 30,
      "offset": 0,
      "returned": 0,
      "has_more": false,
      "next_offset": null
    },
    "boundary": {"execution": "web_native_media_library_read_only"}
  }
  ```

  `boundary` carries literal-false flags for library persistence, collection
  mutation, input persistence, source inspection, provider/catalog/player/
  preview activity, audio/output/job creation, wallet/payment, asset/delivery,
  Bot/Telegram and rights/release approval. It documents a no-execution
  boundary; it is not an execution receipt or delivery promise.

## Truthful no-execution boundary

This is a read transaction only. The library handler does not create or
mutate a collection, item, Asset Vault record, prompt, audio source, output,
job, delivery, idempotency receipt, event, audit record, wallet balance,
payment or rights/release approval. Normal authentication may update
signed-session `last_seen` telemetry before the handler runs; it is not a
Music/SFX Library domain write.

It does not call a provider, Key4U, catalogue/search API, Bot bridge,
Telegram, PayOS, wallet/credit engine, player, preview/stream endpoint or
download adapter. Search is limited to the safe local display projection; it
  does not inspect or upload audio bytes. It searches only the explicit item
  title, collection title and tags; it never searches or returns Asset Vault
  display labels because those can be derived from an uploaded source filename.

## Portal and PWA behavior

- The two pages are Web-native `music-library` layouts, not `readOnlyPage`
  bridge shells and not Bot companion handoffs.
- The browser requests only the owner-scoped `library-items` projection. It
  never falls back to generic `/assets`, invokes an audio player, starts a
  provider/catalog lookup, or presents a fake preview/download state.
- Search, refresh and pagination stay in current tab memory. Delayed replies
  are fenced by route/session epochs and are discarded after sign-out, account
  change or navigation.
- `/music/library`, `/music-library`, `/music/sfx-library`, and the backing
  `/api/v1/media-workspace` namespace are private PWA paths. They are never
  added to the public shell, Cache Storage, offline fallback or browser
  persistence.

## Deliberate exclusions

- The frozen Bot music/SFX callback, cache, provider and delivery families
  remain source-review required. This feature maps or replays none of them;
  the P0 source-review count therefore remains unchanged.
- Music Directions, SFX Cue Sheet, Audio Hub review, generation, uploads,
  source/right validation, playback, export and Asset Vault delivery retain
  their own explicit scopes and security decisions.
- This contract does not alter PayOS, Xu/wallet ledger, jobs, provider
  configuration, Telegram identity, production webhooks or Bot code.
