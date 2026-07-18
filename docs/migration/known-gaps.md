# Known gaps from static audit

| Area | Severity | Count | Finding |
| --- | --- | --- | --- |
| customer_and_admin_routes | high | 0 | Bot source mappings that do not have an observed Web App route or guarded compatibility surface. |
| dynamic_callback_templates | high | 0 | Only templates without a manually reviewed namespace-to-workflow route remain unresolved. A resolved template proves a guarded route family, never a dynamic value or runtime execution. |
| private_core_bridge | high | 1 | Private bridge routes are owned by the separate bot bridge branch, never the browser-facing Web App. Current checkout contract status: BOT_BRIDGE_SOURCE_MISSING |
| telegram_bot_to_web_identity_callback | high | 1 | Direction-specific one-time Telegram callback contract. Current checkout status: CALLBACK_CONTRACT_GAPS_FOUND |
| database_authority | high | 86 | Bot-only tables need read/proxy contracts; the Web App must not duplicate wallet or PayOS writers. |
| feature_surface | medium | 0 | Static feature-token presence differs between bot and Web App; inspect feature-specific routes before enabling a surface. |

These are static findings. Resolve each through contracts and tests before marking a Web App flow complete.

## Additive Web-native guard: Video Poster Lab

Video Poster Lab is intentionally outside the static Telegram mapping counts: it
is a Web-owned utility, not a replacement for a Telegram command. Its code and
schema may exist while the operation stays disabled by default. It must remain
guarded until all of the following are true in the target environment:

- Asset Vault and both Video Poster execution flags are explicitly enabled;
- the isolated private Video Operations root and trusted `ffmpeg`/`ffprobe`
  runtime are available; and
- the deployment explicitly attests `WEBAPP_VIDEO_OPERATIONS_TOPOLOGY=sqlite_single_replica`
  and an available replica-count variable equals exactly `1`; and
- the operator accepts the current bounded request-time model. It has no
  durable queue, retry worker, cross-replica lease or long-form/video-series
  renderer.

This does not change the Bot authority for Telegram identity, Bot jobs,
provider state, Xu/wallet or PayOS. See
[`VIDEO_POSTER_OPERATION_CONTRACT.md`](VIDEO_POSTER_OPERATION_CONTRACT.md).

## Additive Web-native guard: Frame Video Lab

Frame Video Lab is also outside static Telegram command counts. It is a
separate Web-local image-sequence MP4 capability, not a migration of the Bot
worker, long-form/series renderer or provider video generation. It must remain
guarded until Asset Vault, `WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED`, a separate
private root, trusted FFmpeg/ffprobe and explicit one-replica topology are all
enabled. It shares the local FFmpeg gate with Video Poster but has no durable
queue, retry worker, cross-replica lease, audio/mux pipeline, provider adapter
or payment behaviour. See
[`FRAME_VIDEO_LAB_CONTRACT.md`](FRAME_VIDEO_LAB_CONTRACT.md).

## Additive Web-native guard: Video Finishing Lab

Video Finishing is a Web-local bounded reframe/preset utility derived from the
safe local-video-editor concept, not a migration of Bot workers, Video Studio
generation, provider execution or multi-scene/series rendering. It remains
guarded until Asset Vault, `WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED`, an
isolated root, trusted FFmpeg/ffprobe and explicit one-replica topology are
enabled. It shares the single local FFmpeg gate with Video Poster and Frame
Video, has no durable queue, cross-replica lease, text/watermark renderer,
music/voice mux, provider adapter, wallet/Xu or payment behavior. See
[`VIDEO_FINISHING_LAB_CONTRACT.md`](VIDEO_FINISHING_LAB_CONTRACT.md).
