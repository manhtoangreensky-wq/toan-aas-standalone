# Media Factory Blueprint — Web-native contract

## Bot source and scope

This module is the structured Web conversion of the frozen Bot's
`/media_factory <topic>` fallback pack:

- registration: `bot.py` command map (`/media_factory`);
- source pack: `fallback_media_factory_pack()` near `bot.py:88076`;
- related static flow description: `media_factory_overview_text()` near
  `bot.py:87886`.

The Bot pack is content/video planning text. It explicitly keeps customer
live-trend data, real Video AI generation, customer social connection and
customer publish unavailable. The Web conversion retains that boundary.

## Private API

`POST /api/v1/media-factory/blueprint`

The route requires a signed Web session and CSRF proof. Its exact request is:

```json
{"topic":"bình nước giữ nhiệt cho dân văn phòng","language":"vi"}
```

`topic` is one line, 2–180 characters, and rejects markup, URLs/paths,
social handles, secrets, OTP/card-like data and unsafe control characters.
Unknown fields are rejected. A narrow copyright/evasion/impersonation policy
guard returns a truthful `guarded` envelope rather than a plan.

The default-on maintenance switch is `WEBAPP_MEDIA_FACTORY_ENABLED`; setting
it false returns `503` with no fallback plan.

## Result and boundaries

The successful `draft` envelope contains a deterministic `blueprint` with:

- five content angles;
- four manual source keywords and rights guidance;
- a four-step storyboard, six image-scene directions and a text-only video
  direction;
- human review checklist, unavailable capability list and links to the
  separately secured Web workspaces.

Every result includes a full no-execution boundary:

- `input_persisted=false`;
- `live_search_called=false`, `search_provider_called=false`,
  `social_platform_called=false`, `source_content_fetched=false` and
  `source_content_stored=false`;
- `provider_called=false`, `bot_called=false`, `job_created=false`,
  `wallet_mutated=false`, `payment_started=false`, `asset_saved=false`,
  `media_output_created=false`, `publish_action_created=false`;
- `fact_checked=false`, `trend_claim_verified=false`,
  `rights_verified=false`.

The Portal validates the complete schema and this boundary before rendering.
It keeps the receipt only in current signed-session memory; it does not put
the topic or output in Project, Content Studio, Asset Vault, audit detail,
browser storage or the PWA cache.

## Explicit exclusions

This module does **not** call TikTok/YouTube/Facebook/Google Trends, scrape or
fetch source content, call an AI/model/provider, invoke Bot/Core Bridge,
create a job, mutate Xu/wallet, start PayOS, save an asset, make an audio/image
or video, connect a social account, publish, deliver a file or send a webhook.
Each linked workspace retains its own session, CSRF, policy and capability
checks; a blueprint link never grants that next capability.
