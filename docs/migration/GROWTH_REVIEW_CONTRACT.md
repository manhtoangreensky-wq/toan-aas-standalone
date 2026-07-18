# Growth Review — Web-native contract

## Bot baseline translated

- Frozen Bot reference: `bot.py:109800–109860`:
  `calculate_performance_score` and `build_growth_recommendation`.
- Retained rule order: `scale` → `fix_cta` → `fix_hook` → `add_offer` →
  `pause_or_rewrite`.
- Retained score thresholds: views (8/15/25/30), engagement (10/20), clicks
  (5/10/20), value (25/35), capped at 100.
- Excluded deliberately: the Bot's live `/growth_ai` conversation, canonical
  campaign reads, model/provider work, quota/Xu charge/refund and Telegram
  output. The Web module does not import, call or modify Bot code.

## Route and closed request schema

- Portal route: `/growth/ai` (displayed as **Growth Review**, not Growth AI).
- API: `POST /api/v1/growth-review/evaluate`.
- Authentication: signed Web session plus CSRF.
- Raw request cap: 16 KiB; the route has its own fixed request-rate bucket.

```json
{
  "content_label": "Video bình giữ nhiệt tuần 1",
  "platform": "tiktok",
  "views": 10000,
  "likes": 70,
  "comments": 20,
  "shares": 20,
  "clicks": 51,
  "manual_attributed_value_vnd": 100001
}
```

The schema rejects extra fields, floating/string counts, negative/out-of-range
values, unrecognised platforms, multi-line/markup/URL/path/credential-like
labels and unbounded input. `manual_attributed_value_vnd` is an explicitly
manual, unverified value used solely to preserve a rule threshold; it is not a
PayOS transaction, invoice, Bot revenue, wallet balance or Xu ledger value.

## Truthful output boundary

The server returns one transient `draft` receipt containing:

- the six values submitted in this request;
- inspectable score breakdown and fixed rule version `bot-growth-rules-v1`;
- one deterministic recommendation and safe next-workflow links;
- provenance marking platform data as unverified and value as non-canonical.

All execution flags are explicit: no persistence, platform connection/data
verification, canonical-revenue read/write, AI/provider/Bot/Core Bridge call,
job, wallet mutation, PayOS/payment, asset, publishing or delivery.

Neither input nor result is written to a project, analytics report, audit
detail, idempotency table or browser storage. Use Analytics Workspace only if
the signed account deliberately wants to save a separate manual observation.

## Operational guardrails

- `WEBAPP_GROWTH_REVIEW_ENABLED` defaults to `true` because the route only
  evaluates bounded local numbers and has no external execution path.
- PWA must never cache `/growth/ai` or `/api/v1/growth-review` because the
  receipt includes an account-authenticated, user-entered label and metrics.
- The original Telegram `/growth_ai` remains an independent canonical Bot
  workflow; Web must not silently copy its live model, quota or charge logic.
