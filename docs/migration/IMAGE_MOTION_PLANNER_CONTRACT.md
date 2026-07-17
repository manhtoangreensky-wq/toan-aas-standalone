# Image Motion Planner contract

## Bot source mapped

`imagevideo|save` in the frozen Telegram Bot kept a short-lived planning
state after a Telegram image/video wizard. It did not prove a rendered video,
provider call, job, wallet mutation or delivery.

## Web-native replacement

The Web route `/video-studio/image-motion-planner` is a separate signed
workflow:

1. The account selects a currently active Image Studio direction.
2. The server checks, as metadata only, that the direction belongs to that
   account and references an active JPEG/PNG/WebP Image Vault record.
3. The server returns a deterministic three-scene motion plan. It does not
   open, inspect, upload or expose the source image.
4. The customer explicitly confirms a save. The server rechecks ownership and
   metadata, recomputes the plan and creates a private Video Plan Draft.

The browser never sends or receives an asset ID, storage key, source URL,
filename, raw Image Studio prompt, rendered scenes, provider handle, Bot
pending state, job/payment data or lifecycle override for the save.

## API boundary

- `GET /api/v1/video-studio/tools/image-motion-planner/references`
- `POST /api/v1/video-studio/tools/image-motion-planner`
- `POST /api/v1/video-studio/tools/image-motion-planner/save`

The first endpoint uses a signed session. The two writes require a signed
session plus CSRF. Save also requires idempotency and produces a content-free
receipt containing only a plan ID, revision, state and scene count.

## Explicit non-effects

This module never calls the Bot/Core Bridge/provider, opens source media,
creates image/video/audio/preview/output, queues a job, changes Xu/wallet,
starts PayOS/payment, creates an asset, publishes, delivers, approves, locks
or starts generation. The source metadata check is not fact, rights, claim or
consent verification.
