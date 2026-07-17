# Story Video Planner — Web-native contract

## Bot source

This private Web planner combines two adjacent prompt-only Bot commands:

- `/story_video_factory` / `cmd_story_video_factory()` at `bot.py:104354–104370`;
- `/story_motion_prompt` / `cmd_story_motion_prompt()` at
  `bot.py:104372–104387`.

The first Bot command gives a seven-step story workflow and explicitly says
real customer video creation is not automated. The second returns a 12-second
vertical motion prompt, camera direction and style, explicitly marked
prompt-only. Neither command creates a provider job, wallet mutation, payment
or publish action.

## API

`POST /api/v1/media-factory/story-video-plan`

The endpoint requires a signed Web session and CSRF proof. Its exact request:

```json
{"topic":"câu chuyện tự viết về người con trở về quê","language":"vi"}
```

`topic` is required, one line and 2–180 characters. The stricter Web contract
does not silently inject Bot's generic fallback topic. It rejects unknown
fields, markup, URLs/paths, social handles, secrets, OTP/card-like input and
unsafe controls. Copyright-evasion/impersonation/deepfake intent returns a
truthful `guarded` response instead of a plan.

The shared `WEBAPP_MEDIA_FACTORY_ENABLED` maintenance switch can disable this
prompt-only family. It never enables a video provider or render runtime.

## Result boundary

The `draft` response contains seven story steps, a motion prompt, camera/style
direction, four separately secured next-workflow links and a rights/review
checklist. Its status is always `prompt_only_no_real_video`.

Every response declares no input persistence, live/social/source activity,
provider/Bot work, job, wallet/payment, asset, media output, publish action,
fact/trend verification or rights verification. The Portal validates the full
schema before rendering and holds it only in current signed-session memory;
it is excluded from Project, Asset Vault, audit detail, browser storage and
the PWA cache.

There is no crawler, source fetch, video engine, provider, Bot/Core Bridge,
job, Xu/wallet mutation, PayOS, asset save, output, social connection,
publish, delivery or webhook.
