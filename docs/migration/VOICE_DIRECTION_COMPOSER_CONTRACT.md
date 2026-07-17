# Voice Direction Composer contract

## Scope

`POST /api/v1/voice-studio/tools/direction-composer` carries the useful,
text-only direction rules from the local Bot's voice-style suggestions into a
signed, stateless Web receipt.  The Bot source is read-only.  Its six static
profiles are split into the `core` set (`female-soft`, `male-deep`,
`youth-sales`) and the `extended` set (`luxury-cinematic`, `tutorial-clear`,
`faceless-story`); each request shows exactly three.

This is a sibling of the durable Voice Studio/Vault, not a replacement for it.
It does not write vault metadata, retain the script, store raw audio or consent
attestation, select or retain a provider voice ID, call a provider, create TTS,
clone a voice, create preview/audio/output/job, alter wallet/payment/asset
state, or contact Telegram.

## Request

A signed Web session and CSRF header are required.  The request is strict and
does not accept aliases or additional fields.

```json
{
  "text": "Chào mừng bạn đến với sản phẩm mới của chúng tôi.",
  "language": "vi",
  "suggestion_set": "core",
  "selected_suggestion": 2,
  "reading_speed": "normal"
}
```

`text` is 2–260 characters.  `language` is `vi` or `en`; `suggestion_set` is
`core` or `extended`; `selected_suggestion` is an integer from 1 to 3;
`reading_speed` is `slow`, `normal`, or `fast`.

URLs, markup, file/system handles, secret or payment material are rejected.
Requests to clone, imitate, impersonate, or make a voice sound like a real
person, celebrity, artist, singer, or named voice are guarded.  A consent-like
field cannot be supplied to bypass that boundary.

## Success envelope

The response is a text-only direction receipt.  `composer.suggestions` has
exactly three `{choice,id,name,tone,pace,use_case,direction,style_prompt}`
items and `selected_direction` is an exact item from that set.  `delivery_notes`
has exactly `pace_adjustment`, `pause_notes`, `emphasis_notes`, and
`cta_notes`.

```json
{
  "ok": true,
  "status": "draft",
  "data": {
    "composer": {
      "title": "...",
      "text": "...",
      "language": "vi",
      "suggestion_set": "core",
      "selected_suggestion": 2,
      "reading_speed": "normal",
      "suggestions": [{"choice": 1, "id": "female-soft", "name": "...", "tone": "...", "pace": "...", "use_case": "...", "direction": "...", "style_prompt": "..."}],
      "selected_direction": {"choice": 2, "id": "male-deep", "name": "...", "tone": "...", "pace": "...", "use_case": "...", "direction": "...", "style_prompt": "..."},
      "delivery_notes": {"pace_adjustment": "...", "pause_notes": "...", "emphasis_notes": "...", "cta_notes": "..."},
      "cautions": ["..."],
      "review_before_use": ["..."]
    },
    "execution": "web_native_deterministic_voice_direction_only",
    "input_persisted": false,
    "raw_audio_stored": false,
    "consent_attestation_recorded": false,
    "provider_called": false,
    "provider_voice_id_stored": false,
    "tts_called": false,
    "voice_clone_called": false,
    "preview_created": false,
    "audio_created": false,
    "job_created": false,
    "wallet_mutated": false,
    "payment_started": false,
    "asset_saved": false,
    "output_created": false,
    "telegram_called": false
  },
  "error_code": null
}
```

For a non-original or impersonation request the service returns `ok: false`,
`status: "guarded"`, `WEB_VOICE_DIRECTION_ORIGINALITY_GUARD`, and only the
false execution boundary—never a generic voice direction that might be used as
a workaround.

## Web/PWA behavior

`/voice-studio/direction-composer` is a private, non-cacheable screen.  It
holds only a validated receipt in memory and clears it at the next signed
bootstrap.  The UI deliberately contains no preview player, audio URL,
download, TTS, clone, provider, vault-save, job, payment, or delivery control.
