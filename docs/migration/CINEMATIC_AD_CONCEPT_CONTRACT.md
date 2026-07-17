# Cinematic Ad Concept Composer contract

## Scope

`POST /api/v1/video-studio/tools/cinematic-concept` converts the useful,
text-only creative rules from the Bot's cinematic-ad flow into a signed Web
planning receipt.  It is based on the local Bot baseline's style normalization,
three direction choices, motion plans, 5/10/15-second prompt framing, and music
direction vocabulary.  The Bot is read-only and is never imported or started.

The route is a concept planner only.  It does not inspect a source file, call a
provider or bridge, create an image/video/audio/preview/output, queue a job,
write a payment/wallet/asset/publish record, or claim that a fact or right was
verified.

## Request

The route requires a signed Web session and CSRF header.  It accepts a strict
object with no aliases or extra fields:

```json
{
  "product": "Phần mềm quản lý đơn hàng cho shop nhỏ",
  "message": "Giúp chủ shop xử lý đơn nhanh hơn và rõ ràng hơn.",
  "message_theme": "time_save",
  "style": "cinematic",
  "language": "vi",
  "idea_choice": 1,
  "motion_choice": 1,
  "video_duration_variant": 15,
  "music_choice": "1"
}
```

`product` and `message` are each 2–500 characters.  Themes are `memory`,
`success`, `confidence`, `time_save`, `luxury`, `future`, `family`,
`before_after`, or `custom`.  Styles are `cinematic`, `bw_luxury`, `viral`,
`direct_sales`, `ugc`, `fpv`, and `product_reveal`; language is `vi` or `en`.
Creative and motion choices range from 1–3; video duration is 5, 10, or 15;
music choice is `"1"`, `"2"`, `"3"`, or `"none"`.

The server rejects URLs, file/source-media references, markup, secrets, payment
material, system handles and requests to imitate an artist, celebrity or real
person.  Unsupported certainty/medical/performance claims return a guarded
receipt rather than a creative output.

## Success envelope

`data` has exactly `composer` plus the flat execution boundary below.  No
boundary value can be inferred as permission to execute a future workflow.

```json
{
  "ok": true,
  "status": "draft",
  "data": {
    "composer": {
      "title": "...",
      "product": "...",
      "message": "...",
      "message_theme": {"id": "time_save", "label": "..."},
      "style": {"id": "cinematic", "label": "..."},
      "language": "vi",
      "idea_choice": 1,
      "motion_choice": 1,
      "video_duration_variant": 15,
      "music_choice": "1",
      "topic": "...",
      "creative_directions": [{"index": 1, "title": "...", "premise": "...", "brand_story": "...", "hook": "...", "cta": "..."}],
      "selected_direction": {"index": 1, "title": "...", "premise": "...", "brand_story": "...", "hook": "...", "cta": "..."},
      "scripts": {"15s": "...", "30s": "...", "60s": "..."},
      "storyboard": [{"index": 1, "start_seconds": 0, "end_seconds": 3, "setting": "...", "subject": "...", "action": "...", "emotion": "...", "camera": "...", "transition": "...", "voiceover": "...", "cta_space": "..."}],
      "shot_list": ["..."],
      "image_prompts": [{"index": 1, "label": "...", "prompt": "...", "negative_prompt": "..."}],
      "video_prompts": [{"duration_seconds": 5, "prompt": "...", "negative_prompt": "..."}],
      "motion_plan": {"id": "1", "title": "...", "timeline": "...", "camera": "...", "transitions": "...", "shot_direction": "..."},
      "music_direction": {"id": "1", "label": "...", "direction": "...", "ai_music_prompt": "..."},
      "cautions": ["..."],
      "review_before_use": ["..."]
    },
    "execution": "web_native_deterministic_cinematic_concept_only",
    "input_persisted": false,
    "source_media_inspected": false,
    "provider_called": false,
    "image_created": false,
    "video_created": false,
    "audio_created": false,
    "preview_created": false,
    "output_created": false,
    "job_created": false,
    "payment_started": false,
    "wallet_mutated": false,
    "asset_saved": false,
    "publish_action_created": false,
    "fact_checked": false,
    "rights_verified": false
  },
  "error_code": null
}
```

There are exactly three creative directions, three storyboard scenes, three
image prompts and three video prompts (5/10/15 seconds).  The selected
direction matches `idea_choice`; the last storyboard end time matches the
selected duration.  Image/video/music fields are copyable directions only and
must never be rendered as delivery claims.

## Guarded result and client behavior

For an originality/likeness concern, the API returns `ok: false`,
`status: "guarded"`, error code `WEB_CINEMATIC_CONCEPT_ORIGINALITY_GUARD` and
only the false execution boundary.  For unsupported claims it uses
`WEB_CINEMATIC_CONCEPT_CLAIM_GUARD` with the same boundary.  No `composer` is
returned in either case.

The private `/video-studio/cinematic-concept` route and its API response are
never cached by the PWA.  The browser holds a validated receipt in memory only;
it does not create a project, asset, export, job, bridge request or local draft.
