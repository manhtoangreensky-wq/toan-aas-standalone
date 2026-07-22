# Cinematic Ad Concept Composer contract

## Scope

`POST /api/v1/video-studio/tools/cinematic-concept` converts the useful,
text-only creative rules from the Bot's cinematic-ad flow into a signed Web
planning receipt. `POST /api/v1/video-studio/tools/cinematic-concept/save` is a
second, explicit operation that creates a private Web-owned Video Plan Draft
from the original bounded Web inputs. It is based on the local Bot baseline's
style normalization, three direction choices, motion plans, 5/10/15-second
prompt framing, and music direction vocabulary. The Bot is read-only and is
never imported or started.

The compose route is a concept planner only. It does not inspect a source file,
call a provider or bridge, create an image/video/audio/preview/output, queue a
job, write a payment/wallet/asset/publish record, or claim that a fact or right
was verified. The save route has exactly one durable effect: a private,
editable, server-recomputed Web Video Plan Draft. It is not a Bot save, lock,
finalization, render, generation, payment, delivery or publish action.

## Transient compose request

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

`product` is 2–500 characters. With the default `message_mode: "provided"`,
`message` is also 2–500 characters. Themes are `memory`,
`success`, `confidence`, `time_save`, `luxury`, `future`, `family`,
`before_after`, or `custom`.  Styles are `cinematic`, `bw_luxury`, `viral`,
`direct_sales`, `ugc`, `fpv`, and `product_reveal`; language is `vi`, `en`, or
`zh`. The Bot `concept_style_skip` control is normalized explicitly to
`direct_sales`; no raw Bot callback is accepted. Creative and motion choices
range from 1–3; video duration is 5, 10, or 15; music choice is `"1"`, `"2"`,
`"3"`, `"ai_prompt"`, or `"none"`.

`message_mode` is `"provided"` by default or may be `"bot_default"`. For
`bot_default`, the browser sends a blank `message`; the server resolves the
localized built-in default for `vi`, `en`, or `zh` before composing. A nonblank
message with `bot_default` is rejected. This reproduces only the Bot's safe
textual `skip` choice: it does not load pending Telegram state. `ai_prompt` is
also editorial text only; it prepares a music-direction prompt and never
creates audio or calls a provider.

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

## Explicit owner Video Plan save

`POST /api/v1/video-studio/tools/cinematic-concept/save` requires the same
signed session and CSRF proof, plus the same original bounded compose inputs,
an explicit destination and an idempotency key:

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
  "music_choice": "1",
  "destination": "video_plan",
  "idempotency_key": "client-generated-idempotency-key"
}
```

The browser may not send its rendered creative directions, storyboard, prompts,
music text, Bot callback, Bot pending/latest concept, source media, provider
handle, asset, output, lifecycle override or any identifier from Telegram. The
server validates the strict bounded request, recomputes the composer inside the
write transaction, and creates an owner-scoped Web Video Plan with its scenes.
The idempotency key protects this one Web-owned save; it never consumes or
creates a Bot confirmation token.

The successful receipt is content-free except for the destination, private plan
identifier/revision/state and scene count. Its boundary declares:

- `execution: "web_native_video_plan_server_recomputed"`;
- `draft_recomputed_on_server: true` and `web_video_plan_persisted: true`;
- `browser_result_persisted`, `pending_bot_save_created`,
  `telegram_state_changed`, `bot_called`, `bridge_called`,
  `provider_called`, `job_created`, `wallet_mutated`, `payment_started`,
  `asset_saved`, `publish_action_created`, `delivery_created`,
  `approval_created`, `plan_approved`, `plan_locked` and
  `generation_started` are all `false`.

An originality/claim guard returns a content-free `guarded` receipt with
`destination: "video_plan"` and `web_video_plan_persisted: false`; it does not
leave a partial plan. A plan-limit guard likewise never creates a substitute
Bot package or Web media job.

## Frozen Bot callback disposition

The static migration audit resolves `adconcept|` before any generic dashboard,
video or namespace fallback. A Web route in this table is a **fresh signed
navigation only**; it does not carry callback values or resume a Bot
conversation.

| Bot callback family | Audit disposition | Web effect / non-effect |
| --- | --- | --- |
| `start`, `new`, `guided_start`; finite `message` themes; finite `concept_style_*` styles | `NAVIGATION_ONLY` to `/video-studio/cinematic-concept` | Opens an empty signed composer. Product/message/style and Bot pending state are entered again in Web. |
| Bounded `concept_choice`, `motion_choice`, `image_prompt_choice`, `video_prompt_choice`, `music_choice` values `1..3`; `motion_current`, prompt/current/music review actions, `music_ai`/`music_none`, all `save_*`, `back`, `cancel`, `main`, `continue`, `lock`, `back_locked`, `edit_current`, `use_motion_current`, `save_video_package`, `finalize`, and Bot `style|*` | `NEEDS_FEATURE_DISPOSITION` (`BOT_CINEMATIC_AD_TRANSIENT_STATE_NOT_REPLAYED`) | These select, read, clear, edit, lock or save pending/latest/package state for a Telegram user. They do not invoke Web save. A user may separately compose and explicitly confirm an owner Web Video Plan. |
| `image_ai*`, `image_menu`, `video_menu`, `music_menu`, any `create_video_current` / `video_current`, `finalization`, `finalize_video_*`, `trend_current`, `workflow_current`, `music_library`, `music_genre|*` | `NEEDS_FEATURE_DISPOSITION` (`CINEMATIC_AD_RUNTIME_CONTRACT_REQUIRED`) | Provider, active-job, Xu/wallet, music-library, trend/workflow, deferred video-menu or finalization context stays guarded. No provider/job/payment/finalization contract is implied. |
| `admin_video_smoke` / `admin_video_smoke|*` | `TELEGRAM_ONLY` | Bot admin identity plus provider smoke execution remains outside the browser and Admin ERP. |
| stale `image_prompts` or any unreviewed `adconcept|*` spelling | `NEEDS_FEATURE_DISPOSITION` | Fails closed; it cannot inherit a generic Video Studio route or runtime claim. |

### Vocabulary and language limits

The Bot and Web both support Vietnamese (`vi`), English (`en`) and Chinese
(`zh`) for this bounded composer. The Web resolves `message_mode: "bot_default"`
from its own localized table and never reads a Bot-language preference or
pending message. The Bot's motion and music labels also use their own fixed
wording; the Web returns its own deterministic planning labels for the same
bounded ordinal choice. These are Web-native planning semantics, not proof that
a Bot selection, asset or provider output was copied.

## Guarded result and client behavior

For an originality/likeness concern, the API returns `ok: false`,
`status: "guarded"`, error code `WEB_CINEMATIC_CONCEPT_ORIGINALITY_GUARD` and
only the false execution boundary.  For unsupported claims it uses
`WEB_CINEMATIC_CONCEPT_CLAIM_GUARD` with the same boundary.  No `composer` is
returned in either case.

The private `/video-studio/cinematic-concept` route and its API responses are
never cached by the PWA. The compose receipt stays in browser memory only; it
does not create a project, asset, export, job, bridge request or local draft.
Only the separate explicit save route can create the owner Web Video Plan Draft
described above.
