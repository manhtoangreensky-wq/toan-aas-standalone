# Long-form Video Roadmap contract

## Source evidence and current Web surface

The frozen Bot baseline at
`b29d0d474974075f4cba963d2c510f49d2d1b3e4` contains a finite
`longvideo|` editorial wizard in `bot.py`:

- `long_video_start_text` and the topic/duration/style/structure helpers
  (around lines 52856–53279) collect a topic, target duration, visual tone and
  chapter/segment structure;
- `long_video_plan_text` and `long_video_followup_text` (around lines
  53193–53400) create deterministic outline, storyboard, image-prompt,
  video-prompt and voice/music direction text;
- `handle_long_video_callback` (around lines 56013–56200) owns the Telegram
  transitions and separates the editorial follow-ups from finalization,
  image-assembly and segment-render actions.

The standalone Web App now provides the following signed Web route for the
useful editorial workflow:

`/video-studio/long-form-planner`

The route is implemented as a Web-native deterministic planner with
`POST /api/v1/video-studio/tools/long-form-roadmap` and an explicit
`/save` companion. It starts from original Web-owned form values (topic,
duration, style, structure and bounded brief), recomputes the roadmap on the
server, and uses signed-session ownership, CSRF, idempotency and audit logging
for an intentional private Video Plan save. It does not make the route a
provider, job, wallet, payment, media or delivery executor.

## Bot state and database boundary

The Bot holds its wizard state in `USER_PENDING` via
`set_developing_video_pending`, and its latest plan in
`LAST_DEVELOPING_VIDEO_PLANS` via `save_developing_video_plan` (around lines
50868–50967). Both are Bot-process state with TTL behavior; Web must not read,
restore, mutate or rely on either store.

When the Bot reaches a selected structure or receives `longvideo|save`, it can
call `create_long_video_project_from_plan` (around lines 53023–53070). That
function writes the Bot-owned `long_video_projects` and `long_video_scenes`
tables declared around lines 3761–3806. Those rows may contain Bot identities,
scene prompts, Bot image file IDs, Bot video job IDs, output URLs, status and
Xu-related fields.

The Web App does **not** read or write either Bot table, does not synchronize
IDs, and does not treat a Bot project ID as a browser capability. Its current
save creates a separately designed Web-owned draft after server recomputation;
it never duplicates or overwrites Bot ledger, project, scene, job or asset
state.

## Scope of the current planner

The planner may provide only deterministic, editable editorial material:

- outline, chapters and scene goals;
- written storyboard, image direction and video direction;
- voice, music/SFX and CTA/caption guidance;
- a private Web-native Video Plan draft after an explicit, server-recomputed
  save request.

It must not claim any of the following while this contract is in force:

- no Bot callback, Core Bridge request, Telegram pending/session/plan access or
  Bot database write;
- no provider/model call, queue, worker, image/video/audio generation,
  preview, render, mux, output URL, download or delivery;
- no media upload/fetch/inspection/analysis and no use of Bot-held image file
  IDs or video job IDs;
- no Xu/wallet mutation, PayOS/payment/webhook/refund action, price quote,
  invoice or charge;
- no publish, approval, external notification, rights verification or claim
  verification.

## Exact callback disposition

Only reviewed **literal** text-planning callbacks map to the current Web
route. They cover start, topic choices/custom text/refresh/back, the five
literal duration buttons/custom/back, style choices/custom/back, the three
literal structure choices/custom/back, and the `storyboard`, `image_prompts`,
`video_prompts`, `music` and `save` intents.

`longvideo|save` is mapped only as an editorial save intent. It does not grant
the Web permission to invoke `create_long_video_project_from_plan`, write
`long_video_projects`/`long_video_scenes`, or represent a Bot project as a Web
draft.

The following execution-boundary callbacks remain `TELEGRAM_ONLY`:

| Bot callback | Why it stays outside the Web planner |
| --- | --- |
| `longvideo|finalization` | Opens the Bot finalization/invoice path. |
| `longvideo|frame_video` | Can consume Bot-held segment image state and enter image assembly. |
| `longvideo|render_segments` | Observes/starts the Bot provider job/finalization path. |

No `longvideo|{*}` namespace rule is added. In particular, an unknown action
or a future dynamic structure value cannot inherit this route; it requires
source evidence and its own reviewed Web contract.
