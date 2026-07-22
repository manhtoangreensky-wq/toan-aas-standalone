# Script-to-Screen Planner Contract

## Purpose

The Web-native Script-to-Screen Planner translates the useful **text-first**
portion of Bot Task3D `vproduct` into a signed Web workflow.  It has two
customer-facing project kinds:

- `script_image_video` — **Kịch bản → Ảnh → Video**
- `multi_scene_film` — **Phim dài tập** (the stored key deliberately remains
  stable for existing requests and future drafts)

The Bot reference is reviewed from the immutable baseline
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`, Task3D `vproduct` helpers and
handlers around lines 47367–49277. The adaptation deliberately does not copy
its conversation/session, media input, prompt vault, package, renderer, or
provider execution paths.

## Web contract

| Operation | Route | Durable effect |
| --- | --- | --- |
| Compose a review pack | `POST /api/v1/video-studio/tools/script-to-screen-planner` | None. Returns deterministic text direction only. |
| Save a reviewed plan | `POST /api/v1/video-studio/tools/script-to-screen-planner/save` | Creates one private, Web-owned Video Plan draft after server recomputes all scenes from bounded source inputs. |
| Customer page | `/video-studio/script-to-screen-planner` | Signed session and CSRF are required for both actions. |

`multi_scene_film` remains a compatibility identifier; the UI and API label
present it as **Phim dài tập / Episodic series**. It is now an actual bounded
season roadmap rather than a renamed flat multi-scene pack:

- a Script → Image → Video plan is exactly one episode;
- each episode has 3–16 base reviewable planning scenes, with a clear 0, 1
  or 2 extra-scene choice; the final storyboard is capped at 18 scenes;
- an episodic series has 2–8 episodes, each carrying the same bounded scene
  count in its editorial roadmap;
- the browser selects one episode to expand into script, storyboard and prompt
  direction;
- one explicit save creates **only that selected episode** as one private
  Web-owned Video Plan draft. It never creates a season, batches episodes,
  starts a render, schedules a job or claims a delivered series.

The season map, continuity bible and episode handoff notes remain deterministic
editorial text. They are not provider state or a claim that a rendered or
published series exists.

## Frozen Bot callback boundary

Only these exact, case-sensitive Bot literals are recorded as a fresh Web
navigation intent:

- `vproduct|ideas|script_image_video`
- `vproduct|input_text|script_image_video`
- `vproduct|ideas|multi_scene_film`
- `vproduct|input_text|multi_scene_film`

They open a blank signed `/video-studio/script-to-screen-planner` form. They
do not prefill a product, selected idea, platform, panels, style, color, pace,
image plan, scene count, prompt, media, package, Xu, job or payment state.
Even `vproduct|open|script_image_video` and
`vproduct|open|multi_scene_film` remain Bot-session evidence, not Web
navigation. Every dynamic `vproduct|open|{*}` value and every unreviewed
spelling fails closed for source review.

The detailed callback table is generated in
[`VPRODUCT_CALLBACK_CONTRACT.md`](VPRODUCT_CALLBACK_CONTRACT.md).

## Explicit non-goals

This module does **not**:

- call Telegram, the Bot, a bridge, a provider, renderer, or preview service;
- receive source media or create image/video/audio, jobs, assets, outputs, or
  delivery;
- change Xu, payments, PayOS, or publication state;
- trust browser-composed storyboard output during the durable save.

The compose response proves all of those actions are false.  The save response
proves `draft_recomputed_on_server=true` and
`web_video_plan_persisted=true`, while the same execution fields remain false.

## Safety and ownership

All requests use the signed Web session and CSRF protection.  Inputs are strict
and bounded; unsafe imitation and unverified-claim directions return a guarded
envelope. The save endpoint accepts a client idempotency key, recomputes the
selected episode server-side, creates a private owner-only Video Plan, and
writes an audit event. Its tags identify the selected `season-{count}` and
`episode-{index}` only for internal organization; they are not provider,
runtime or delivery identifiers. No Bot state is read or mutated.

The UI treats a composed pack as stale as soon as any source field or selected
episode changes. It never issues a save idempotency key until the visible form
normalizes to the exact source used for the current result; late compose/save
responses are fenced by account, route, session and request epochs.
