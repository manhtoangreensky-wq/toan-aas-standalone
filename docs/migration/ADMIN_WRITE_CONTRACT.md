# Guarded Admin ERP write contract

The Web App exposes these controls only as a thin, feature-gated client of the
canonical Bot. This file does not enable a production write adapter, change
wallet/PayOS logic, or modify `bot.py`.

## Default posture

`WEBAPP_ADMIN_WRITES_ENABLED=false` by default. With the flag off, server
routes still require a signed local admin session and CSRF before returning a
guarded response; they never contact the Bot. The portal renders disabled
controls with an explicit explanation instead of pretending a write completed.
`WEBAPP_ADMIN_ERP_ENABLED` is also required; when it is off, Web returns a
guarded result before the live canonical-role re-check or any write bridge call.

## Compatibility routes without a Bot adapter

The migration matrix maps a large number of historical Bot admin commands to
signed `/admin/*` compatibility pages. A page is not allowed to turn that map
into an arbitrary private-bridge request. The Portal keeps a code-owned list
of current Bot read adapters; any other compatibility module renders a local
`guarded` envelope with no Bot, provider, Xu, PayOS, job or write call.

The HTML route itself still requires a signed session and a current canonical
admin role before it is rendered. The guarded page intentionally has no
metric, record, retry/refund/freeze control or browser-supplied identity. It
becomes a real read/write Web module only after the Bot publishes a narrow
adapter and the method/path/schema/role contract is tested.

## Available write intents

| Portal action | Web API | Canonical bridge target |
| --- | --- | --- |
| Retry a failed/cancelled job | `POST /api/v1/admin/jobs/{id}/retry` | `POST /internal/v1/admin/jobs/{id}/retry` |
| Request a refund review | `POST /api/v1/admin/jobs/{id}/refund` | `POST /internal/v1/admin/jobs/{id}/refund` |
| Freeze/unfreeze a feature | `POST /api/v1/admin/features/{feature}/freeze` | `POST /internal/v1/admin/features/{feature}/freeze` |

Every intent is limited to canonical route identifiers, asks for a visible
confirmation, requires a non-blank 5–300-character operation note for freeze,
adds a unique idempotency key, and sends the signed Web CSRF token. Before a
write reaches the bridge, the Web server performs both:

1. local signed-session + CSRF + cached-admin gate; and
2. canonical Bot role re-check through `require_canonical_admin_csrf`.

The Bot remains authoritative for job state, charge/refund eligibility,
feature readiness, provider state, maintenance policy, audit outcome and
customer messaging. The browser cannot supply a Telegram identity, force a
status, or directly call a provider.

Every accepted or gated Web write intent also creates a sanitized
`web_audit_events` record (action, canonical target, coarse outcome and
request ID only). It never stores a provider response, payment reference,
customer data, credential or raw bridge payload.

After an acknowledged response, the portal discards the browser idempotency
key. A later deliberate retry/refund/freeze is a fresh canonical intent;
only an interrupted request retains its key for safe retry.

## Enablement checklist

Do not set the flag merely because the portal controls are visible. Before any
production enablement, the private Bot bridge must implement and test all
three target routes with role checks, one-time idempotency, audit logging,
refund policy and provider/job safeguards. Then configure Railway:

```text
WEBAPP_ADMIN_ERP_ENABLED=true
WEBAPP_ADMIN_WRITES_ENABLED=true
WEBAPP_COPYFAST_ENABLED=true
```

The task has not enabled these variables or performed a live operation.

## Test boundary

Automated tests mock the bridge and verify that disabled writes do not make a
bridge call, enabled writes perform both local/canonical admin checks, retry,
refund and freeze preserve distinct idempotency keys, and browser controls are
still confirmation- and capability-gated.
