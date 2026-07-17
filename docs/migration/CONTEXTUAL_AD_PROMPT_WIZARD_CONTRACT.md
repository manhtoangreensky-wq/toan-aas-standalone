# Contextual Ad Prompt Wizard — Web-native contract

## Bot source

This Web tool converts the frozen Bot's local contextual Meta-prompt wizard:

- option labels and navigation: `bot.py:46732–46788`;
- pending-state transitions: `bot.py:59850–59907`;
- deterministic helper: `free_tools_hub.py:265–323`,
  `generate_contextual_prompt()`.

The Bot stored one topic and four selected values in a short-lived Telegram
pending record before assembling a prompt. The Web replaces that UI state with
one signed, CSRF-protected form: `topic`, `goal`, `platform`, `aspect_ratio`
and `style`. The source helper is deterministic; it does not call Meta,
another provider, a Bot engine, a job or the Xu ledger.

## API

`POST /api/v1/content-studio/tools/contextual-ad-prompt`

Exact request shape:

```json
{
  "topic": "Bình nước giữ nhiệt cho dân văn phòng",
  "goal": "sell",
  "platform": "tiktok",
  "aspect_ratio": "9:16",
  "style": "real"
}
```

Allowed choices faithfully carry the Bot wizard grammar:

- goal: `sell`, `engage`, `brand`, `story`;
- platform: `facebook`, `reels`, `tiktok`, `shorts`;
- ratio: `9:16`, `16:9`, `1:1`, `4:5`;
- style: `real`, `cinematic`, `fun`, `luxury`, `ugc`.

The endpoint requires a signed Web session and CSRF proof, rejects unknown
fields, secrets, OTP/card/payment-like text, unsafe controls and originality
evasion. It shares `WEBAPP_CONTENT_STUDIO_ENABLED` only as a maintenance
switch; that flag does not enable Meta, a social account, provider, Bot,
renderer, job, wallet, PayOS, asset or publishing capability.

## Result and boundaries

Success returns exactly one `plan` with Bot-derived industry/audience hint,
goal/platform/ratio/style, a 12-second primary prompt, three fixed variants,
caption/hashtags/CTA, shot list, negative direction, music/SFX direction and
human review checklist.

The full execution boundary is false for input persistence, provider/Bot,
jobs, wallet/payment, assets, media output, publishing, fact checking and
rights verification. The plan remains only in current signed Portal state; it
is never written to Content Studio, Project, audit detail, browser storage or
PWA cache.

The tool never calls Meta or any provider, connects social accounts, fetches
audience/trend data, creates a campaign/ad/video/image/audio, runs a job,
changes Xu/payment, saves an asset, publishes, delivers a file or sends a
webhook. Claims, rights, consent, brand safety and final creative quality
remain the user's review responsibility.
