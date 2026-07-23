# Music Directions preset contract

## Purpose and authority

`/media-workspace/music-directions` is an independent signed Web-native text-planning surface. It is deliberately **not** an adapter for the frozen Telegram Bot's `suggest_music|*` callback family. The Bot remains frozen at `b29d0d474974075f4cba963d2c510f49d2d1b3e4`; its five callbacks reply with a Bot `/music_library` keyword and stay `SUGGEST_MUSIC_SOURCE_REVIEW_REQUIRED` in the parity audit.

The page offers five reviewed, opaque Web preset IDs:

| Web `web_preset_id` | User-facing direction |
| --- | --- |
| `commercial_bright` | Thương mại sáng |
| `technology_future` | Công nghệ tương lai |
| `cinematic_brand` | Cinematic thương hiệu |
| `warm_story` | Kể chuyện ấm |
| `short_viral` | Short-form bắt nhịp |

These identifiers are Web-only contract values. Their server-owned mapping to deterministic prompt-composer hints is not a browser-supplied mode, catalog choice, Bot preset or `/music_library` search keyword.

## Explicit Web flow

1. A signed Web account selects one radio preset. Selection changes only the local form state: it must not navigate, reset history, send a request, call a provider or submit automatically.
2. The user enters a new description and explicitly chooses **Lập music directions**.
3. The browser sends a CSRF-protected request to `POST /api/v1/media-workspace/tools/music-directions/compose` with the exact strict JSON shape:

```json
{
  "description": "Mô tả mới do người dùng nhập",
  "language": "vi",
  "web_preset_id": "commercial_bright"
}
```

The strict schema forbids unknown fields, and `web_preset_id` must exactly match one lower-case value in the finite allowlist. Case variants, suffixes, raw `suggest_music|*` callback values, Bot mode/selection internals, and every unreviewed ID are rejected. As a description, a raw callback, a full Bot `/music_library` command, or an exact bare Bot keyword is rejected; ordinary prose is never interpreted or forwarded as a Bot preset, catalog, provider, playback, job, wallet or delivery action. The server derives its own finite hint mapping; the browser never selects an internal suggestion set or choice.

## Bounded result

On a valid explicit request, the service returns only a deterministic, transient text-planning receipt with:

```text
execution = web_native_deterministic_music_direction_only
input_persisted = false
source_audio_inspected = false
provider_called = false
ai_music_called = false
lyrics_generated = false
audio_created = false
preview_created = false
output_created = false
job_created = false
wallet_mutated = false
payment_started = false
asset_saved = false
collection_saved = false
publish_action_created = false
telegram_called = false
rights_verified = false
```

It may present three text directions for manual review. It does not save to Memory, create an audio file or player, inspect source audio, call the Bot, Key4U, Suno or another provider, create a job, calculate or mutate Xu, start/finalize PayOS, save an asset/collection, publish, or claim delivery. The result is not evidence of generated music, playback rights, license clearance, provider availability or delivery.

## Callback boundary remains unchanged

The independent page does not give browser meaning to any original Bot callback. All of these remain source-review-only and must not acquire a Web route, browser action or request parameter:

- `suggest_music|sales`, `suggest_music|tech`, `suggest_music|cinematic`, `suggest_music|review`, and `suggest_music|trend`;
- every case variant, missing token, suffix, unknown value, or future `suggest_music|*` value.

No Web request may forward a raw Bot callback, Telegram identity/context, keyword, cache index, selected media, provider result, wallet/payment state, job identifier, output or delivery state. A future real audio/catalog experience requires its own owner-scoped, reviewed execution and delivery contract.
