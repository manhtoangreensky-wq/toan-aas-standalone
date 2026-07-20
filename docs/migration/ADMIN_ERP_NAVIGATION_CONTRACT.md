# Admin ERP navigation contract

`GET /api/v1/admin/navigation` is the single server-authorized directory for
the Web App's Admin ERP sidebar, command palette and module directory. It is
not an ERP data API and it never substitutes for a module's own authorization.

## Authority domains

| Domain | Server check | Current surfaces | Boundary |
| --- | --- | --- | --- |
| Canonical Admin | Signed Web session plus live `require_canonical_admin` confirmation | Command Center, Commerce, Delivery & Runtime, Content/Growth directory, Governance | The Bot/Core Bridge remains authoritative for identity, wallet/Xu, PayOS, jobs, provider state and canonical write rules. |
| Web Support | Signed Web session plus `require_support_staff` | Support Desk, Operations, Reliability | Web-owned case and metadata workflow only; it cannot mutate Bot, PayOS, wallet, provider jobs, deployment, delivery or customer notification. |
| Web Local Admin | Signed Web session plus local `require_admin` | CRM Manager Directory, Automation Monitor, Governance Documents, Internal Document Archive, Security & Access Posture | Identifier-free Web-owned read models only; this does not grant canonical Bot admin authority or session/MFA/role control. |

A cached browser role, `admin_id`, email allow-list or query parameter never
creates an Admin navigation entry. For a non-admin account, the response is a
successful guarded envelope with an empty `groups` array. The browser fails
closed if the endpoint is unavailable.

## Response shape

```json
{
  "ok": true,
  "status": "read_only",
  "message": "Đã nạp điều hướng Admin ERP theo quyền server-side hiện tại.",
  "data": {
    "groups": [{
      "id": "delivery_runtime",
      "title": "Delivery & Runtime",
      "authority": "canonical_admin",
      "modules": [{
        "id": "jobs",
        "title": "Jobs",
        "route": "/admin/jobs",
        "source": "core_bridge",
        "availability": "canonical_read",
        "capability": "canonical_read"
      }]
    }],
    "access": {
      "canonical_admin": true,
      "web_support": false,
      "web_support_scope": "none"
    },
    "boundaries": ["..."]
  },
  "error_code": null
}
```

The endpoint returns no customer records, counters, bridge payloads, provider
configuration, secrets, raw audit data, account identifiers or write tokens.
`availability` is navigation metadata, not a claim that an engine, payment,
delivery or write adapter is live.

## Write safety

This endpoint has no mutation route. A module may expose a write only when its
own handler applies the appropriate signed authority, CSRF, confirmation,
idempotency, revision/policy checks and audit event. Navigation must never
enable retry, refund, freeze, manual top-up, provider control, role change,
deployment or external notification.
