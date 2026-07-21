# Admin Security & Access Posture contract

`/admin/security` and `/admin/access` are two views of one signed,
Web-native, read-only posture projection:

```text
GET /api/v1/admin/security-posture/summary
```

They require the server-side `require_admin` role and are independently
disabled by `WEBAPP_ADMIN_ERP_ENABLED`. They do not inherit canonical Bot
Admin authority because the projection only concerns storage owned by this
Web App.

## Safety boundary

- The endpoint reads only fixed aggregate buckets from Web account, session,
  MFA, throttle and audit tables. It returns no account/session/factor/challenge
  identifiers, contact data, token, CSRF value, password/ciphertext/hash,
  recovery code, OAuth subject, client information, request ID, audit detail
  or raw action.
- Unknown state, role or outcome makes the complete numeric view `guarded`.
  The browser must not keep or render prior aggregates for a guarded result.
- The Portal only uses `cache: "no-store"`, a session/route epoch fence and a
  strict DTO validator. Private `/admin` paths remain excluded from the PWA
  shell cache.
- There are no mutation routes and no controls for role grant/revoke, session
  revocation, MFA reset, credential changes, configuration, deployment or
  repair.
- It never calls Bot/Core Bridge, provider, PayOS, Xu/wallet, jobs, webhook or
  deployment services.

## Retired compatibility route

Historic generic bridge paths below are explicitly retired before any
canonical-admin or bridge dependency is resolved:

```text
GET /api/v1/admin/modules/security
GET /api/v1/admin/modules/access
```

They return `404`. Generic bridge projections also do not expose arbitrary
`reason` or `action` strings.

## Envelope

The browser receives the standard envelope with only `read_only` or `guarded`
status. Its data root identifies source and policy version
`web_security_access_posture_v1`, includes fixed read-only boundaries, safe
feature availability, and identifier-free aggregates. When `integrity_guarded`
is true, all numeric aggregates are hidden rather than approximated.

This is a posture display, not a claim that a security action was performed or
that a provider/canonical system is configured.
