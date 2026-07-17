# Video Factory Workflow — Web-native contract

## Bot source

This is the private Web navigation conversion of the frozen Bot helper
`video_factory_flow_text()` at `bot.py:87962–87990`, exposed through
`/video_factory_flow` (`bot.py:128963`). The Bot helper itself has no input,
database write, provider call, job, wallet, payment, asset or publish action.

It describes seven phases: trend/insight, content direction, image/scene
planning, rights-aware editing, content/video pack, review and an explicitly
admin-only/non-public publish phase. It also warns against crawler/reup,
watermark/DRM/Content ID evasion and unconsented real-person deepfakes.

## Web route

`/video-studio/workflow` is a signed-session, read-only page. It has no API
form and sends no data. It only links to separately secured Web workspaces:
Trend Research, Creative Flow, Content Prompt Pack, image/storyboard/video
planners, Subtitle/Voice direction, Media Factory, Music Prompt, Workboard,
Approvals and Support.

The route requires the existing `WEBAPP_VIDEO_STUDIO_ENABLED` readiness flag
and signed session to render its private workflow view. It never transfers
input, grants the next tool's capability, or lifts that next tool's CSRF,
session, ownership or policy check.

## Exclusions

It does not run live trend/social search, fetch source content, call an
AI/provider or Bot/Core Bridge, create a job, mutate Xu/wallet, start PayOS,
save an asset, render media, connect a social account, publish, deliver a file
or send a webhook. Customer auto-publish and social-platform APIs remain
guarded, exactly as the Bot flow states.

The PWA treats the route as private and never caches it. This page is a
navigation map only, not a claim that video generation or publishing has been
configured.
