# Audio Hub Collection Review Pack — Web-native contract

## Purpose

`POST /api/v1/media-workspace/collections/{collection_id}/review-pack` creates
a **transient, deterministic checklist** for the exact signed Web collection
and revision currently open at `/audio-hub/{collection_id}`. It helps an
editor see whether brief/reference metadata needs attention before consciously
opening a separate specialist workflow.

It is not a new Audio Hub authority. `/audio-hub` remains a visual projection
of the existing owner-scoped Media Workspace API; this endpoint adds no
`audio_hub` table, Bot mapping, collection history, idempotency receipt,
event, audit event, provider catalog, player or delivery model.

## Request and lifecycle

```json
{
  "expected_revision": 7
}
```

- Requires a signed Web session and CSRF.
- Collection UUID is owner-scoped server-side; a UUID alone never authorizes a
  review.
- Requires the exact active revision. A stale revision, foreign collection,
  archived collection or policy-marked brief is guarded.
- The browser does not send a new brief, filename, asset ID, URL, rights note,
  license text, Bot callback, Telegram identifier, provider selection or
  approval flag.
- The handler opens its collection/item data through a read transaction only.
  Normal signed-session `last_seen` telemetry may be touched by authentication
  before the handler; the review itself does not write `web_media_*`,
  `web_idempotency`, audit/event data or any new table.

## Safe receipt

The response contains only:

- collection UUID and revision;
- finite `review_state` (`needs_brief`, `needs_reference_metadata`, or
  `human_review_required`);
- count-only music/SFX/reference metadata signals;
- a fixed four-step checklist and fixed cautions.

It never echoes `creative_brief`, description, rights note, attribution,
license note, asset UUID, filename, digest, storage key, path or URL.

Every receipt declares literal false values for collection mutation,
persistence, approval, source inspection, provider/catalog/player/preview,
audio/output/job creation, wallet/payment, asset/delivery, Bot/Telegram,
rights verification and release approval. A review receipt is therefore never
a license clearance, a completed audio action or a release decision.

## Portal behavior

The only trigger is on the private Audio Hub collection detail surface. It
sends the currently rendered UUID and revision to the existing Media Workspace
namespace, fences delayed replies by signed-session/route/revision epochs, and
keeps the receipt in current tab memory only. Detail/list hydration, a route
change, sign-out or account change clears it. No query string, browser
storage, PWA private cache, auto-navigation or automatic handoff is used.

## Deliberate exclusions

- The frozen Bot `audio_hub` callback family remains source-review required;
  this Web review pack neither maps nor replays its pending state, caches,
  profile IDs, provider calls, Xu/wallet/payment flow or Telegram delivery.
- No provider, Key4U, Suno, music/SFX catalog, audio generation, preview,
  waveform, source analysis, output validation, job, playback or file delivery
  is introduced.
- Existing Music Directions, SFX Cue Sheet and Audio Operations remain separate
  workflows. The pack does not prefill or transfer collection/source data to
  any of them.
