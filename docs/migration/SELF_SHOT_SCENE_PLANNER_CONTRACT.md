# Self-shot Scene Planner contract

## Source evidence and designated Web surface

The frozen Bot baseline at
`b29d0d474974075f4cba963d2c510f49d2d1b3e4` implements `selfscene|` in
`bot.py` around `handle_self_scene_ai_callback` (around lines 55683–56008).
It is a Telegram conversation that can retain a recent Telegram video/file ID
and then collects:

- the subject that should remain stable;
- an editorial direction and a target context;
- camera motion plus optional music/SFX guidance; and
- a text-only video/keyframe prompt package.

The designated standalone Web surface is:

`/video-studio/self-shot-planner`

The signed implementation exposes a bounded **text scene-direction planning**
grammar at `/api/v1/video-studio/tools/self-shot-scene-planner` and a distinct,
explicit owner-scoped Video Plan Draft save endpoint. It does not add a media
endpoint, provider adapter, Bot integration, or a claim that the Bot workflow
or a media transformation has been executed.

## Consent and right-to-use boundary

The Web planner requires a clear, affirmative acknowledgement before it
creates even a transient direction pack:

- the customer owns the source or has the necessary right to use it;
- every recognisable person has consent for the requested transformation;
- the request does not impersonate, deceive, create a non-consensual
  likeness/deepfake, or misrepresent a person, product, affiliation or event;
- the customer will obtain any further brand, music, location or talent rights
  required before production or publication.

That acknowledgement is a customer assertion, not a verification service.
The planner must not claim to authenticate identity, confirm consent, clear
rights, assess copyright, or prove that a later output is lawful. Risky or
ambiguous requests need human review before any separate production system.

## Exact no-execution boundary

The planner is text direction only. It must not:

- accept, store, replay, resolve, expose, or derive a Telegram file ID, recent
  media slot, chat ID, message ID, Bot session, or Bot plan;
- upload, fetch, open, decode, inspect, sample, transcribe, analyse, preview,
  or transform a video, image, frame, audio file, URL, or asset;
- call Telegram, the Bot, a Core Bridge, a model, or a media/provider API;
- create an image, video, audio, frame set, job, output, download, preview,
  delivery, invoice, charge, Xu mutation, PayOS operation, publish action, or
  provider status record;
- persist a Bot plan, a memory record, an asset, a browser-generated result,
  or a source-media reference.

The signed Web route may, after a separate explicit Save confirmation, rebuild
the bounded text choices on the server and create an owner-scoped `VideoPlan`
Draft. That narrow Web persistence is not the Bot's `selfscene|save`: it has
CSRF, idempotency, ownership and audit controls; it stores no Telegram file
ID/source media; and it does not start a provider, render, job, payment,
asset, publish or delivery action.

The Bot's `selfscene|save` label remains only a non-persistent session save in
Bot. The standalone Web App exposes a different, explicitly labelled
`Save as Video Plan Draft` handoff; it is never presented as a Bot save or a
completed media transformation.

In the Bot, a motion or music selection can first write a short-lived
`LAST_DEVELOPING_VIDEO_PLANS` record and then open its finalization flow. The
Web mapping intentionally stops before both effects: it represents only the
editorial selection and must not recreate an automatic package, invoice,
render, or provider transition.

## Callback disposition

The audit maps only literal, source-reviewed text-planning transitions to
`/video-studio/self-shot-planner` as `COPIED_GUARDED`, including:

- start and plan-without-video entry;
- direction, subject, context, motion, music and back/refresh/custom text
  choices; and
- plan, keyframe-prompt guidance, music suggestions, and the Bot's
  non-persistent save intent.

The following stay `TELEGRAM_ONLY` because they depend on a Telegram
media/session slot or enter a finalization/runtime path:

- `selfscene|await_video`, `selfscene|use_recent_video`, and
  `selfscene|input|video`;
- `selfscene|back_upload`;
- `selfscene|video_guard`, `selfscene|frame_hint`, and
  `selfscene|finalization`.

There is deliberately no `selfscene|{*}` mapping. A future callback—especially
one that starts a provider, render, frame, package, payment, job, preview, or
delivery action—must receive its own source evidence and contract before it is
shown anywhere in the Web App.
