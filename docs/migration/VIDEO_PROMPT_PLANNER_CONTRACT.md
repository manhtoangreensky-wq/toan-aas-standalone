# Video Prompt Planner contract

## Purpose and source boundary

`POST /api/v1/video-studio/tools/prompt-planner` is a signed, stateless Web-native
planning tool.  It adapts the useful text-only planning rules in the local Bot
baseline — flow selection, motion normalization, intent parsing, scene breaking,
prompt rendering and validation — into a reviewable video brief.  The Bot is read
only; this endpoint does not import or start Bot code.

It is deliberately a plan, not a render request.  It never claims that a source
image/video was inspected, a provider was contacted, a preview/output exists, a
job was queued, or a wallet/payment/asset/publish action occurred.

## Request

The route requires the normal signed Web session and CSRF header.  It accepts a
strict JSON object only:

```json
{
  "mode": "prompt_to_video",
  "brief": "Giới thiệu nhanh ứng dụng quản lý đơn hàng cho cửa hàng nhỏ.",
  "platform": "tiktok",
  "ratio": "9:16",
  "duration_seconds": 20,
  "scene_count": 4,
  "style_pack": "app_saas_explainer",
  "action_pack": "ai_dashboard_reveal",
  "audio_mode": "voiceover_vi",
  "detail_level": "viral",
  "motion": "camera push-in nhẹ",
  "background": "không gian làm việc sáng, gọn",
  "must_keep": ["logo ở đoạn kết"],
  "must_avoid": ["cam kết doanh thu"],
  "language": "vi"
}
```

Allowed `mode` values are `prompt_to_video`, `trend_video`, `storyboard_video`
and `long_script`.  It uses the compact, reviewed portal packs only:

- Styles: `corporate_tech_commercial`, `product_luxury_reveal`,
  `tiktok_viral_product_demo`, `ugc_review_style`, `documentary_premium`,
  `emotional_storytelling`, `app_saas_explainer`, `food_commercial`.
- Actions: `product_spin_reveal`, `logo_product_hero_shot`, `slow_push_in`,
  `before_after_wipe`, `phone_screen_transition`, `walk_through_reveal`,
  `ai_dashboard_reveal`, `customer_pain_to_solution`.
- Audio cues: `modern_electronic`, `cinematic_light`, `asmr_only`,
  `voiceover_first`, `voiceover_vi`, `emotional_piano`, `office_ambience`,
  `silent`.

`language` is request-only.  `duration_seconds` must be 3–180; `scene_count`
is 0–10 and allows the planner to select a safe scene count when zero.  The
service rejects markup, private/sensitive material, direct imitation, real-person
deepfake or unreviewed rights claims before planning.

## Success envelope

Every response uses the public envelope:

```json
{
  "ok": true,
  "status": "draft",
  "message": "Đã tạo plan video để bạn rà soát trước khi sản xuất.",
  "data": {
    "planner": {
      "title": "...",
      "mode": "prompt_to_video",
      "brief": "...",
      "platform": "tiktok",
      "ratio": "9:16",
      "duration_seconds": 20,
      "scene_count": 4,
      "style_pack": {"id": "app_saas_explainer", "label": "..."},
      "action_pack": {"id": "ai_dashboard_reveal", "label": "..."},
      "audio_mode": {"id": "voiceover_vi", "label": "..."},
      "detail_level": "viral",
      "needs_clarification": false,
      "motion": "...",
      "background": "...",
      "must_keep": ["..."],
      "must_avoid": ["..."],
      "continuity_locks": ["..."],
      "coverage": {"ok": true, "missing": []},
      "cautions": ["..."],
      "review_before_use": ["..."],
      "prompt": "...",
      "negative_prompt": "...",
      "shots": [{
        "index": 1,
        "start_seconds": 0,
        "end_seconds": 5,
        "beat": "...",
        "visual": "...",
        "action": "...",
        "camera": "...",
        "transition": "...",
        "audio": "..."
      }]
    },
    "execution": "web_native_deterministic_video_plan_only",
    "input_persisted": false,
    "source_media_inspected": false,
    "provider_called": false,
    "video_created": false,
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

The plan contains no `language` field because language controls generation only
and is not a durable state claim.  The execution boundary is deliberately flat
inside `data` alongside `planner`, matching the existing stateless portal
contracts.  Clients must validate both exact shapes before displaying a result.

## Non-goals and safety

The endpoint has no media upload/URL/source-inspection path and no bridge,
provider, model, storage, queue, database, payment, wallet, asset, webhook or
publishing dependency.  It stores no request/result, creates no audit or job
record, and does not make “trending”, factual, rights, or delivery guarantees.
The service worker must not cache the route or API response as private content.
