# Channel Strategy Contract

## Purpose

The frozen Bot baseline's `videoref` flow collects a compact channel profile:
platform, niche, tone, target audience, blocked topics, affiliate choice and
goal.  The Web App adopts that useful planning grammar as a professional,
signed-account workspace instead of copying the Telegram conversation or its
single active profile state.

Web users can keep multiple private profiles, version changes, archive or
restore a profile, and request a deterministic direction for human review.

## Routes and persistence

| Operation | Route | Durable effect |
| --- | --- | --- |
| Summary | `GET /api/v1/channel-strategy/summary` | None |
| List private profiles | `GET /api/v1/channel-strategy/profiles` | None |
| Read one private profile | `GET /api/v1/channel-strategy/profiles/{id}` | None |
| Create | `POST /api/v1/channel-strategy/profiles` | Profile, version 1, sanitized event and audit label |
| Update | `PATCH /api/v1/channel-strategy/profiles/{id}` | New optimistic-revision snapshot, event and audit label |
| Archive / restore | `POST /api/v1/channel-strategy/profiles/{id}/{archive|restore}` | New lifecycle snapshot, event and audit label |
| Direction preview | `POST /api/v1/channel-strategy/profiles/{id}/strategy-preview` | Sanitized `strategy_previewed` event/audit label only; no profile or strategy persistence |
| Customer pages | `/content/channel-strategy`, `/content/channel-strategy/{id}` | Signed-session portal pages; never PWA-cached |

The additive tables are:

- `web_channel_strategy_profiles`
- `web_channel_strategy_profile_versions`
- `web_channel_strategy_events`

Every durable write uses CSRF, account ownership, optimistic revision,
idempotency and audit logging.  The browser gets content-free mutation
receipts and rehydrates the profile from the server; it never invents a
successful write or restores a profile from browser storage.

## Boundary

Channel Strategy is deliberately Web-owned authoring and review metadata.  It
does not:

- read or modify Telegram identity, Bot conversation/pending state or Bot
  channel-profile storage;
- fetch a channel URL, query social platforms, trends, audience data,
  analytics, reach or conversion;
- call a provider, create a media request/job/output/asset, publish content or
  create delivery;
- alter Xu, wallet, PayOS, pricing, payment, refund or webhook state.

All response envelopes expose these false side effects.  The preview is marked
`web_native_deterministic_channel_strategy_preview_only` and
`strategy_persisted=false`; it is a review aid, not a forecast or automated
content plan.

## Safety

Input is strict and bounded.  The server rejects unsafe control characters,
markup, secrets/tokens/OTP/payment data, non-HTTPS channel URLs, imitation of
identified people/creators, and unverified absolute claims.  Professional
negative compliance notes such as “không cam kết kết quả” remain allowed.

The service worker has explicit private-route exclusions for both the API and
portal paths.  The generic canonical/bridge hydrator is also excluded from
this native route family.

## Follow-on workflow

The direction may link a user to Content Studio, Content Prompt Pack or
Workboard.  Those remain separate contracts: no link automatically creates a
brief, social action, schedule, job or publish request.
