# Creative Flow Composer — Web-native contract

## Bot source

The Web route is a direct, structured conversion of the frozen Telegram Bot:

- command registration: `CommandHandler("creative_flow", cmd_creative_flow)`
  at `bot.py:128956`;
- input/handler: `cmd_creative_flow()` at `bot.py:88461–88468`;
- deterministic source template: `creative_flow_text()` at
  `bot.py:88434–88459`.

The Bot command takes an idea and returns local template guidance: a short
script, image prompt, image-story direction, music/SFX search brief,
caption/hashtags, CTA and next steps. It does not create a job, call a
provider or charge Xu. The Web conversion preserves that truth boundary.

## API

`POST /api/v1/media-factory/creative-flow`

The endpoint requires a signed Web session and CSRF proof. Its exact request:

```json
{"idea":"video quảng cáo máy xay sinh tố mini TikTok 15 giây","language":"vi"}
```

`idea` is one line and 2–180 characters. It rejects unknown fields, markup,
URLs/paths, social handles, secrets, OTP/card-like data and unsafe controls.
The same narrow originality/copyright-evasion/impersonation guard as Media
Factory returns a truthful `guarded` envelope instead of content.

`WEBAPP_MEDIA_FACTORY_ENABLED` is the shared maintenance switch for this
static media-planning family. It does not enable any provider or execution.

## Result and limits

Successful requests return a `draft` `flow` with five script steps, one image
direction, one image-story direction, music and SFX briefs, caption/hashtag,
CTA, four validated links to separately secured Web workspaces and a three-item
human review checklist.

The full no-execution boundary always reports false for input persistence,
live/social/source activity, provider/Bot calls, job/wallet/payment, assets,
media output, publishing, fact/trend verification and rights verification.
The result lives only in current signed Portal state and is never stored in
Project, Asset Vault, Content Studio, audit detail, browser storage or PWA
cache.

This endpoint never searches a music/SFX catalog, creates image/video/audio,
calls provider/Bot/Core Bridge, creates a job, changes Xu/wallet, starts PayOS,
stores an asset, connects a social account, publishes, delivers a file or
sends a webhook.
