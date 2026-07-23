# SFX Cue Sheet Composer contract

## Purpose and authority

`/media-workspace/sfx-cue-sheet` is an independent signed Web-native editorial planning surface. It is deliberately **not** an adapter for the frozen Telegram Bot's `sfx_quick|*` callbacks, `/sfx_library` command, provider search, preview/select keyboard or media cache. This Web-only contract does not modify Bot code, Bot state, provider configuration, Xu, PayOS, jobs or Telegram delivery. The Bot remains frozen at `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

The frozen Bot SFX picker contains `whoosh`, `click`, `cinematic`, `notification` and `pop` actions under Telegram product context; its custom-SFX entry is also a `music_quick|custom_sfx` callback. The Bot's `send_sfx_library_results` can call its configured Freesound path, save a per-user preview cache and expose Telegram preview/select controls. None of that runtime behavior is copied into Web.

The page instead offers five reviewed, opaque Web preset IDs:

| Web `web_sfx_preset_id` | Editorial intent |
| --- | --- |
| `motion_transition` | Chuyển động mượt |
| `interface_confirm` | Xác nhận giao diện |
| `reveal_impact` | Điểm nhấn mở lộ |
| `status_signal` | Tín hiệu trạng thái |
| `caption_emphasis` | Nhấn caption |

These identifiers are server-owned Web contract values. They are neither Bot action names nor catalog keywords, and they do not select a provider, library result, preview, asset, job, audio file or output.

## Explicit Web flow

1. A signed Web account selects one native radio preset. Changing that local selection must not navigate, reset history, send a request, search a catalog, call a provider or submit automatically.
2. The user writes a new editorial brief and explicitly chooses **Lập SFX cue sheet**.
3. The browser sends a CSRF-protected request to `POST /api/v1/media-workspace/tools/sfx-cue-sheet/compose` with the exact strict JSON shape:

```json
{
  "description": "Mô tả mới do người dùng nhập",
  "language": "vi",
  "web_sfx_preset_id": "motion_transition"
}
```

The strict schema forbids unknown fields. `language` is exactly `vi` or `en`, and `web_sfx_preset_id` must exactly match one lower-case reviewed value. Case variants, suffixes, unreviewed IDs, raw `sfx_quick|*` or `music_quick|*` callback values, a full `/sfx_library` command, preview/select syntax and an exact bare Bot SFX keyword are rejected. Ordinary prose that merely mentions a sound term is never interpreted or forwarded as Bot input.

## Bounded result

A valid explicit request returns a deterministic, transient text receipt with exactly three ordered semantic cue positions: `opening`, `transition` and `closing`. These are editorial placements only. The service does not receive, open or inspect a video/audio source, so it must not fabricate duration, millisecond timestamps, waveform positions, beat detection or a synchronized timeline.

```text
execution = web_native_deterministic_sfx_cue_sheet_only
input_persisted = false
source_video_inspected = false
source_audio_inspected = false
catalog_searched = false
provider_called = false
sfx_generated = false
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

The receipt may contain only textual cue role, direction, mix, avoid and editorial-review notes. It does not search Freesound or another catalog, create/play/preview/download/upload audio, call the Bot or a provider, create a job, calculate or mutate Xu, start/finalize PayOS, save Memory/asset/collection state, publish or claim delivery. It is not evidence that a sound, timing, license, rights clearance, provider result or output exists.

## Callback boundary remains unchanged

Every original Bot SFX callback remains `AUDIO_HUB_SOURCE_REVIEW_REQUIRED`, including exact values, context forms, case variants, missing tokens, suffixes and future `sfx_quick|*` values. `music_quick|custom_sfx` and related Audio Hub actions remain source-review-only too. No Web request may forward a raw Bot callback, Telegram identity/context, cache index, provider result, selected media, preview value, wallet/payment state, job identifier, output or delivery state. A future real SFX catalog or execution experience requires its own owner-scoped, reviewed bridge/execution and delivery contract.
