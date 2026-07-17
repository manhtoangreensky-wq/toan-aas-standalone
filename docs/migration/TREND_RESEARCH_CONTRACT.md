# Trend Research Plan — Web-native contract

## Bot baseline translated

- Frozen Bot reference: `bot.py:88170–88208`, command registration
  `bot.py:128930–128934`.
- Bot input: `/trend_research <ngách/chủ đề>`.
- Bot behaviour retained: five keyword variations, manual research surfaces,
  five trend-selection criteria, four originality guardrails and next steps.
- Bot-only paths explicitly excluded: `/trend_ai` (AI/Xu/job), `/trend_live`
  (admin/provider/live search), and `/tool_test_trend_live` (admin/provider
  test). They are not silently reimplemented in the browser.

## Web route and request

- Portal route: `/trend-research`.
- API: `POST /api/v1/trend-research/plan`.
- Authentication: signed Web session plus CSRF.
- Exact JSON body:

```json
{"topic":"bình nước giữ nhiệt","language":"vi"}
```

`topic` is a single 2–180 character line. The strict schema rejects extra
fields, URL/path/file/markup/social-handle input, credentials, OTP/card data
and policy-guarded reup/watermark/DRM/Content-ID evasion, impersonation,
clone or real-person deepfake requests.

## Truthful output boundary

The response is a transient `draft` with a deterministic plan only. It always
reports `manual_content_only` and `not_live_not_verified`; it does **not**
claim fresh, verified or platform-derived trend data.

Every successful or guarded response carries explicit false execution flags:
no input persistence, live/social/search-provider call, remote-source fetch or
storage, provider/Bot call, job, wallet/Xu, PayOS, asset/media output, publish
action, fact check, trend verification or rights verification.

The plan is never written to a Web project, Content Studio, audit detail,
browser storage or an idempotency table. The user must manually verify source
content, facts, timing, claims and rights before moving selected insight into
Content Prompt Pack, Image Prompt Composer or Video Prompt Planner.

## Operational guardrails

- `WEBAPP_TREND_RESEARCH_ENABLED` is a maintenance switch; it defaults to
  enabled because this text-only checklist has no external execution path.
- Requests have a 16 KiB raw-stream limit and a fixed pre-router rate limit.
- PWA never caches `/trend-research` or `/api/v1/trend-research`.
- No Bot source, payment/webhook, provider configuration or production
  integration changes are part of this contract.
