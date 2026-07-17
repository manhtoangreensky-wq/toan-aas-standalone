# Video Idea Planner contract

## Source evidence and Web replacement

The frozen Bot baseline at
`b29d0d474974075f4cba963d2c510f49d2d1b3e4` registers the `videoidea|`
callback handler in `bot.py` and implements a temporary Telegram conversation:

- `video_idea_menu_keyboard` begins with advertising, cinematic, or custom
  ideas (`bot.py` around lines 54024–54034);
- the surrounding helpers collect product/topic, goal, context, three concept
  choices, storyboard, image/video direction and audio notes;
- `handle_video_idea_callback` (around lines 56355–56597) stores temporary
  Bot state, shows the selected text package, and exposes follow-up callbacks;
- `finalization`, `frame_video`, and `render_ai` leave the planning boundary:
  they enter the Bot finalization/runtime path, can depend on Bot-held scene
  images, or inspect an active Bot video job.

The standalone Web replacement is:

`/video-studio/idea-planner`

It condenses the useful editorial grammar into a signed Web form. The customer
selects idea kind, product type, topic, audience, goal, context, platform,
language, duration, idea set, idea choice and (when needed) a custom brief.
The server returns three original concepts, a selected concept, a six-scene
storyboard, image/video direction text, audio notes, caption, hashtags and a
human-review checklist.

The Bot remains read-only reference material. The Web neither imports nor
updates its pending/session/plan records.

## APIs and persistence

| Endpoint | Authentication | Effect |
| --- | --- | --- |
| `POST /api/v1/video-studio/tools/video-idea-planner` | Signed Web session + CSRF | Generates a transient deterministic editorial plan only. |
| `POST /api/v1/video-studio/tools/video-idea-planner/save` | Signed Web session + CSRF + idempotency key | Recomputes the plan from bounded original choices inside the transaction and creates one private Web `draft` Video Plan with six scenes. |

The compose request is strict (`extra=forbid`) and accepts only supported enum
values, a 15/30/45/60-second duration, bounded text, and an explicit choice
from three ideas. A custom idea needs a custom brief. The planner guards direct
imitation/likeness wording and claims that need a source or verification before
it returns a plan.

The save request accepts original choices only. It never accepts browser-made
scenes, an asset ID, source media, a provider/job handle, a lifecycle override,
or a Bot result. The response is a compact receipt with the private plan ID,
revision, state and scene count; the server writes the audit event
`web.video.idea_planner.save_plan`.

## Exact execution boundary

The transient planner result and explicit save both:

- do not create or change Telegram/Bot state and do not call a Core Bridge;
- do not accept, upload, fetch, open, inspect, decode or analyze source media;
- do not call a provider or model, and do not create image, video, audio,
  preview, output or a job;
- do not mutate Xu/wallet, start PayOS/payment, save an asset, publish,
  approve, lock, start generation or deliver anything;
- do not fact-check claims, verify rights, identity, consent or ownership.

Saving is intentionally the sole durable Web effect: a server-recomputed,
account-owned Video Plan Draft. It is not a render request or a claim that any
of the text directions can be produced by a provider.

## Bot callback disposition

The audit maps only the literal Bot callbacks whose behavior is a finite
text-planning choice to `/video-studio/idea-planner` as `COPIED_GUARDED`:

- start/kind, product/topic, goal/context and cinematic/genre choice steps;
- back/refresh/choice transitions;
- selected-package text follow-ups (`storyboard`, `image_prompts`,
  `video_prompts`, `music`) and the text-plan `save` intent.

`videoidea|finalization`, `videoidea|frame_video`, and
`videoidea|render_ai` remain `TELEGRAM_ONLY`. They rely on a separate
finalization/runtime or Bot image/job state and must not be turned into a
browser navigation that suggests a payment, render, preview or delivery.

The legacy literal platform/trend keyboard callbacks are also
`TELEGRAM_ONLY`: the frozen `handle_video_idea_callback` has no matching
transition for them. No generic `videoidea|{*}` mapping is added; future Bot
actions need individual evidence and an independently reviewed Web contract.
