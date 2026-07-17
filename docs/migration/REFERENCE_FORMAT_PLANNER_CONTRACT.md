# Reference Format Planner Contract

## Bot source and Web replacement

The local Bot `videoref` flow receives a Telegram video/link, holds temporary
state for direction/topic/channel choices, then creates a text planning pack.
Its own planning step does not prove that a renderer, provider, job, Xu charge,
publish action or delivered video exists.

The Web-native replacement is:

`/video-studio/reference-format-planner`

It accepts a selected **active owner-scoped Asset Vault video**, a new topic,
audience, platform, goal, tone, language and planning duration. It produces a
deterministic original three-scene plan and can save it as a private Web Video
Plan only after explicit confirmation.

## Exact execution boundary

The planner:

- checks signed session, CSRF and owner scope;
- selects only active `web_asset_files` metadata for MP4, M4V, MOV or WebM;
- does **not** select a storage key, URL, original filename, video bytes,
  duration, frames, transcript, preview or provider metadata;
- does **not** open, download, decode, sample, inspect or analyze the video;
- does **not** fetch a URL, call Telegram/Bot/Core Bridge/provider, create
  image/video/audio/preview/output/job, mutate Xu/wallet, start PayOS, save an
  asset, publish or deliver content;
- does **not** verify facts or rights. It rejects narrow direct imitation or
  likeness wording and requires human review before a later workflow.

The save endpoint recomputes the full plan from original bounded choices inside
the write transaction. Browser-generated scenes, source media, external links,
provider/job data and lifecycle fields are not accepted. The response receipt
is content-free and identifies only the created Web Video Plan ID/revision.

## APIs

| Endpoint | Authentication | Effect |
| --- | --- | --- |
| `GET /api/v1/video-studio/tools/reference-format-planner/references` | Signed Web session | Lists compact owner-scoped active video metadata only. |
| `POST /api/v1/video-studio/tools/reference-format-planner` | Signed session + CSRF | Returns a transient deterministic plan; no persistence or execution. |
| `POST /api/v1/video-studio/tools/reference-format-planner/save` | Signed session + CSRF + idempotency key | Rechecks ownership, recomputes plan and creates one private `draft` Video Plan with three scenes. |

## Bot parity mapping

Core static `videoref` callbacks map to this explicit Web workspace, including
hub/start/temporary direction/topic/profile choices, plan refresh and save.
The Web does not import a Bot file ID or assume a channel integration.

- Bot link ingestion stays outside scope: the Web user first uploads a video
  they are allowed to use into Asset Vault.
- Bot auto-publish remains unavailable; its Web route is the manual
  Publish Review Pack only.
- Bot performance input maps to the independently owned Analytics Workspace.
- A later production integration may add a separately audited video-analysis
  adapter; it must not silently change this planner into an analysis/render
  endpoint.
