# Engine and delivery adapter backlog

This is the narrow handoff required to turn the already-routed Web workflows
into real canonical jobs. It is not an instruction to enable a provider from
the browser or to duplicate Bot wallet/PayOS logic in the Web App.

## Current fact

The local Bot bridge supports safe draft/estimate paths for the mapped
workflows, but its generic confirm path deliberately returns
`CANONICAL_JOB_ADAPTER_REQUIRED`. This is correct: a generic provider call
cannot prove a single ledger charge, a durable Bot job, validated output, or
private customer delivery.

The Web App therefore keeps feature confirmation, video finalization/mux and
file delivery guarded until the following Bot-owned adapters exist.

## Required Bot-owned adapter contract

For each executable feature family, the private Core Bridge must implement a
feature-specific confirm path behind the existing shape:

```text
POST /internal/v1/features/{feature}/confirm
```

It must accept only the authenticated canonical user and the same
idempotency key used by the Web request. A successful response must include
only this browser-safe tracking reference:

```json
{
  "ok": true,
  "status": "queued|processing|completed|failed|guarded",
  "message": "Vietnamese public message",
  "data": {
    "tracking": {
      "id": "canonical-job-id",
      "feature": "exact-feature-key",
      "status": "queued|processing|completed|failed"
    }
  },
  "error_code": null
}
```

The adapter must atomically:

1. Revalidate ownership of every staging upload/asset reference.
2. Revalidate the estimate receipt/input fingerprint and feature readiness.
3. Create exactly one canonical job for the idempotency key.
4. Charge/refund only through the Bot ledger policy.
5. Record a canonical audit event and expose the job through `/jobs`.
6. Never expose provider task IDs, local paths, raw provider responses or
   temporary delivery URLs in the confirm response.

## Delivery contract

After the Bot marks output as validated, it must offer an owner-scoped
temporary delivery adapter for the existing Web download route. The adapter
must confirm all of the following before returning a URL/redirect:

- The job and asset belong to the requesting canonical user.
- The output exists, passed validation and has a completed canonical job.
- The URL is short-lived and audience-bound where supported.
- A failed/retried job cannot expose an earlier invalid or cross-user output.
- Download decisions create a sanitized audit event without storing the URL
  in the Web App database.

The Web browser must never derive a delivery URL from `output_available`, a
provider handle, job timestamp, filename or a Bot database path.

## Feature-family order

| Priority | Family | Existing Web surface | Adapter outcome required |
| --- | --- | --- | --- |
| P0 | Image/video single-job | `/image/*`, `/video/*` | one canonical job, owner-scoped validated asset |
| P0 | Voice/music | `/voice/*`, `/music/*` | policy/consent check, job, validated audio delivery |
| P0 | Subtitle/dubbing | `/subtitle`, `/translate`, `/dubbing` | ASR/translation/TTS/mux state with honest fallback outputs |
| P0 | Documents | `/documents/*` | local-worker result validation and private download |
| P1 | Video finalization | `/video/add-ons`, `/video/mux` | exact source job/assets, mux/burn status and atomic result delivery |
| P1 | Admin writes | `/admin/*` | canonical permission, confirmation, idempotency and audit for each mutation |

## Verification gate

The first adapter is ready only when mocked tests prove:

- duplicate confirms do not create/charge two jobs;
- a failed output is not shown as completed;
- retry/refund follows Bot policy exactly once;
- a different canonical user cannot read the job or download its asset;
- a copied/superseded URL and a replayed callback are rejected;
- Web receives only the explicit tracking reference, never a provider or
  ledger implementation detail.

Until those tests exist on the Bot branch, `WEBAPP_PROVIDER_CALLS_ENABLED`
and Web feature confirmation remain safely disabled by default. When an
individual adapter passes, enable it explicitly with both the global review
gate and an exact allowlist key, for example:

```text
WEBAPP_FEATURE_JOB_ADAPTER_ENABLED=true
WEBAPP_FEATURE_JOB_ADAPTERS=video_single
```

Adding `video_single` permits only that feature's confirmation. It does not
make image, voice, music, subtitle, document or finalization workflows
executable until each has its own reviewed key.
