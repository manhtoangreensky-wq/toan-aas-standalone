# Storyboard Prompt Pack Composer → Video Plan contract

`POST /api/v1/video-studio/tools/storyboard-composer` remains a signed-session,
CSRF-protected **request-only** deterministic composer. It persists nothing.

`POST /api/v1/video-studio/tools/storyboard-composer/save` is the separate,
explicit Web-native handoff. Its strict body is the original composer inputs
only, plus:

```json
{
  "destination": "video_plan",
  "idempotency_key": "client-generated-idempotency-key"
}
```

The endpoint rejects browser-generated `composer`, plan, scene, project,
provider, job, asset, payment, wallet, Bot or lifecycle fields. It requires a
signed Web session, CSRF token and the Video Studio feature gate.

Inside one Web database transaction the server recomputes the deterministic
Storyboard Composer result and creates an owner-scoped draft `web_video_plan`,
its immutable first plan version, editable active scenes, first scene versions,
Studio events, one sanitized audit event and an idempotency receipt. The saved
plan begins at `draft`; it is not approved or locked.

The response and idempotency receipt contain only the destination, plan ID,
revision/state, scene count and explicit boundary facts. They intentionally
exclude topic, brief, generated prompts and scene text. The owner can retrieve
the private content through the existing Video Studio plan route.

This adapts the useful static `storypack|save` intent from the Telegram Bot,
but it never imports, runs, reads or writes Bot state. It does not create a
Telegram pending save, call a bridge/provider, inspect media, create a job or
asset, mutate wallet/payment, approve/lock a plan, start generation or deliver
media. Claim/originality/likeness guards remain truthful and create no plan.
