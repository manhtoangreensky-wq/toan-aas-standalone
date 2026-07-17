# Music Prompt Composer contract

## Scope

`POST /api/v1/media-workspace/tools/music-prompt-composer` adapts the local
Bot's static music-prompt rules into a signed, stateless Web planning receipt.
The Bot source is read-only: its mode detection, copyright-safe wording and
first/next-three suggestion rotation are used as a reference only.

The tool does not inspect source audio, call Suno or another provider, generate
lyrics/audio/preview/output, create a job, change wallet/payment state, save an
asset or collection, create a publish action, or contact Telegram.  Existing
Audio Library/Media Workspace collections remain a separate durable feature.

## Request

The route requires a signed Web session and CSRF header.  It accepts no aliases
or unknown keys.

```json
{
  "description": "Nhạc nền gọn cho video giới thiệu ứng dụng quản lý đơn hàng",
  "mode": "background",
  "language": "vi",
  "suggestion_set": "primary",
  "selected_suggestion": 1
}
```

`description` is 2–500 characters.  Modes are `background`, `lyrics`,
`melody`, `script`, and `custom`; language is `vi` or `en`; suggestion set is
`primary` or `alternate`; selection is 1–3.

URLs, files, markup, opaque system handles, secrets and payment material are
rejected.  Requests to recreate, imitate or borrow a named artist, singer,
song, melody, beat, vocal identity or copyrighted style return a guarded
receipt.  A rights note is not an authorization to bypass that boundary.

## Success envelope

`composer` has exactly these fields:

```text
title, description, mode, language, suggestion_set, selected_suggestion,
suggestions, selected_direction, usage_notes, cautions, review_before_use
```

There are exactly three `suggestions`; each is
`{choice,name,mood,tempo,instruments,duration,vocal,lyric_direction,use_case,prompt}`.
`selected_direction` is an exact suggestion.  `usage_notes` has exactly
`voice_mix_notes`, `edit_notes`, `rights_notes`, and `delivery_notes`.

```json
{
  "ok": true,
  "status": "draft",
  "data": {
    "composer": {"title": "...", "suggestions": [{"choice": 1, "prompt": "copy-only music direction"}]},
    "execution": "web_native_deterministic_music_prompt_only",
    "input_persisted": false,
    "source_audio_inspected": false,
    "provider_called": false,
    "ai_music_called": false,
    "lyrics_generated": false,
    "audio_created": false,
    "preview_created": false,
    "output_created": false,
    "job_created": false,
    "wallet_mutated": false,
    "payment_started": false,
    "asset_saved": false,
    "collection_saved": false,
    "publish_action_created": false,
    "telegram_called": false,
    "rights_verified": false
  },
  "error_code": null
}
```

Copyright/originality concerns return `ok: false`, `status: "guarded"`,
`WEB_MUSIC_PROMPT_COPYRIGHT_GUARD`, and only the flat false boundary; no music
direction is returned as a workaround.

## Web/PWA behavior

`/media-workspace/music-prompt-composer` is a private non-cacheable route.  Its
receipt exists only in authenticated in-memory UI state.  It offers no audio
player, provider request, Suno action, download, collection-save, job, payment
or delivery action; prompts are copy/review text only.

## Explicit save to Memory Center

`POST /api/v1/media-workspace/tools/music-prompt-composer/save` is a separate,
explicit action for the reviewed selection. It preserves the useful static
"save current result" intent from the Bot while not reading, creating or
changing any Bot pending state. The Bot source remains read-only reference;
the Web owns the saved note.

The save route requires:

- a signed Web session and matching CSRF token;
- `WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED=true`;
- `WEBAPP_MEMORY_CENTER_ENABLED=true`;
- the original bounded Composer inputs, `destination: "memory_note"`, and a
  12–160 character idempotency key.

The browser may not send a generated result, prompt/body/title, account ID,
asset, collection, provider reference or alternate destination. The server
recomputes the exact selected direction in its write transaction, then creates
one owner-scoped `web_memory_notes` row, one revision and one Memory event. It
does not write a Media Workspace collection/item/event.

```json
{
  "description": "Nhạc nền gọn cho video giới thiệu ứng dụng quản lý đơn hàng",
  "mode": "background",
  "language": "vi",
  "suggestion_set": "primary",
  "selected_suggestion": 1,
  "destination": "memory_note",
  "idempotency_key": "music-prompt-memory-save-0001"
}
```

The successful receipt contains only note metadata:

```json
{
  "ok": true,
  "status": "completed",
  "data": {
    "note": {
      "id": "uuid",
      "revision": 1,
      "state": "active",
      "category": "Music Prompt Composer",
      "priority": "normal"
    },
    "destination": "memory_note",
    "execution": "web_native_memory_note_server_recomputed",
    "draft_recomputed_on_server": true,
    "web_note_persisted": true,
    "browser_result_persisted": false,
    "pending_bot_save_created": false,
    "telegram_state_changed": false,
    "bot_called": false,
    "bridge_called": false,
    "source_audio_inspected": false,
    "provider_called": false,
    "ai_music_called": false,
    "lyrics_generated": false,
    "audio_created": false,
    "preview_created": false,
    "output_created": false,
    "job_created": false,
    "wallet_mutated": false,
    "payment_started": false,
    "asset_saved": false,
    "collection_saved": false,
    "publish_action_created": false,
    "delivery_created": false,
    "fact_checked": false,
    "rights_verified": false
  }
}
```

The deterministic note body is retrievable only through the signed owner’s
Memory Center route. The 24-hour idempotency receipt and audit event retain no
description, selected prompt or other creative text. Reusing a key with
different original inputs returns `409`; a copyright/originality guard returns
no note and leaves all durable stores unchanged.
