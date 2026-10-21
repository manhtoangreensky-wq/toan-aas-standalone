# MU-E — Music/SFX library read-only surface

## CONTRACT

Scope: `/music/library` and `/music/sfx-library` metadata-only customer views.
The current renderer is intentionally owner-scoped and read-only: it shows
reference name, collection, tags, duration and update time; it does not open
audio, player, download, provider search, Bot handoff or payment. This spec
closes the presentation/runtime gate without inventing missing management
capabilities.

Allowed: existing `static/portal/portal.js`/`portal-i18n.js` library paths,
focused test/evidence/checklist/state. Protected: media-workspace editor and
asset operations, backend list contract, provider, wallet/PayOS, auth and
motion.

## Acceptance

1. Music and SFX roles filter separately; invalid role/id rows are hidden.
2. Loading/failed/guarded/empty states hide stale data and stay VI/EN/ZH clean.
3. Ready cards are escaped, vertical/mobile-safe and link only to the
   owner-scoped collection route; no audio/player/download/private URL.
4. Search/refresh controls remain capability-gated and read-only.

## Verify

`node --test tests/music-library-locale-purity.test.mjs` plus browser QA on
both routes with guarded/ready/empty fixture states → zero page/console/
external/mutation errors. Provider calls and wallet mutations remain zero;
LIVE is not claimed.
