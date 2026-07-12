# Guarded feature-confirm contract

The Web App may prepare a feature draft and ask the canonical Bot for an
estimate, but it never creates a provider task itself.  The final confirm is
therefore intentionally behind a separate gate:

```text
WEBAPP_COPYFAST_ENABLED=true
WEBAPP_PROVIDER_CALLS_ENABLED=true
WEBAPP_FEATURE_JOB_ADAPTER_ENABLED=false
WEBAPP_FEATURE_JOB_ADAPTERS=
```

`WEBAPP_FEATURE_JOB_ADAPTER_ENABLED` remains **false** in this task.  Turning
on provider calls alone must not make a Web confirm available.  The portal
also requires a configured private bridge before rendering the confirm action.
Even after the global adapter switch is approved, `WEBAPP_FEATURE_JOB_ADAPTERS`
must name each exact canonical key (for example `video_single`) that has a
reviewed Bot confirm adapter. Unknown, read-only, admin and empty values are
ignored. A single approved feature must never open confirm for all Web routes.

## Required Bot bridge contract before enablement

Only after the Bot implements and tests
`POST /internal/v1/features/{feature}/confirm` may the adapter flag be set and
that exact `{feature}` placed in `WEBAPP_FEATURE_JOB_ADAPTERS`.
For every request, the Bot must independently:

1. derive the canonical Telegram user from the signed bridge request and
   verify feature ownership;
2. verify a fresh canonical quote/input digest rather than trusting browser
   JavaScript state;
3. enforce idempotency across job creation, charging and retries;
4. decide charge, refund, provider selection, job state and audit outcome;
5. return `queued`, `processing`, `failed`, or `guarded` as appropriate — not
   a synthetic `completed` state or output URL.

The Web request carries only a bounded feature input and idempotency key.  It
does not receive provider credentials, wallet balance decisions, job/provider
handles, raw output, or a download URL.  Completed work continues to be read
through canonical jobs/assets, and file delivery stays on the separate signed
asset-delivery contract.

## Exact Job Center handoff after confirm

When (and only when) a reviewed Bot adapter accepts a confirm, it may return
this narrow, owner-scoped response field:

```json
{
  "tracking": {
    "id": "canonical-job-id",
    "status": "queued",
    "feature": "video_single"
  }
}
```

The Web server forwards it only if all of the following are true:

1. `tracking.id` is a bounded canonical identifier;
2. `tracking.status` is a real job lifecycle state (`queued`, `processing`,
   `completed`, `failed`, `failed_no_charge`, `cancelled`, or `refunded`);
3. `tracking.feature` equals the top-level canonical feature and exists in the
   Web registry.

The Portal verifies the same fields again before rendering **Theo dõi job**.
It then opens the normal ownership-checked `/jobs/{id}` page, where status
polling and asset delivery remain separate canonical reads. It never guesses a
job by timestamp, feature name, output path or provider handle. If the bridge
does not provide this exact reference, the Portal offers only a generic Job
Center link and explicitly says that no job has been matched to the request.

The tracking object is not a delivery channel: URLs, output/file metadata,
provider task IDs, payment/ledger fields and identity fields are redacted.

## Guarded Bot-menu continuation

When a Web feature has no reviewed confirm adapter, the Portal may show a
user-initiated **Mở Bot / `/menu`** handoff. It is navigation only: no feature
input, prompt, upload ID, Telegram ID, quote receipt, Xu amount, session,
token or provider data is copied into Telegram. The customer chooses the Bot
workflow again inside the canonical conversation. This is not a successful
confirm, provider call, job, payment or output claim.

## Web estimate receipt

After a successful `awaiting_confirm` estimate, the Web server creates a
one-time opaque `web_quote_receipt`. It is bound to the signed Web session,
Web account, canonical Telegram identity, feature key, normalized input digest
and a maximum ten-minute expiry. SQLite stores only hashes and binding/timing
metadata — never the raw receipt, prompt, file metadata, price, provider,
payment, job or output data.

`confirm` must return that same receipt. The server atomically reserves it for
one idempotency key: a retry with that key is permitted, while a direct confirm
without a receipt, a changed input/session/account, an expired receipt, or a
different key is guarded before any Bot bridge call. The receipt is a Web
freshness check only; it never reaches the Bot and cannot authorize a quote,
charge, refund, provider task or job by itself.

## Safety boundary

This change does not modify `bot.py`, enable an environment variable, call a
provider, create a PayOS order, write Xu, or deploy Railway.  Tests mock the
private bridge and assert that a duplicate confirm reuses its idempotency
result rather than creating a second canonical request.
