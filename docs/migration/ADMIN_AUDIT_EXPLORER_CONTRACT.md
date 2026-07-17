# Admin Audit Explorer contract

`GET /api/v1/admin/audit-events` gives a live canonical Admin a bounded,
read-only projection of `web_audit_events` owned by the standalone Web App.

It is intentionally not the Bot/Core Bridge audit API. The endpoint does not
select or return account IDs, canonical Telegram IDs, request IDs, targets,
details, free-form customer text, secrets, provider data, payment references,
wallet/Xu data, jobs or deployment information.

## Access and filters

- Requires `require_canonical_admin` for every request.
- Requires `WEBAPP_ADMIN_ERP_ENABLED`; otherwise returns a guarded empty
  envelope after authority verification.
- Accepts only `category` values: `all`, `auth`, `support`, `operations`,
  `workspace`, `content`, `asset`, `admin`, `security`.
- `limit` is server-bounded to 1–100. There is no free-text or ID search.

Each result contains a reviewed category label, an allowlisted/redacted event
label, a normalized state, a human outcome label and timestamp. Unknown raw
action names are collapsed to a generic redacted label rather than echoed.

## Boundaries

- No mutation endpoint, export, webhook, provider call or background action.
- No replacement for Bot canonical audit history.
- Audit browsing does not authorize retry, refund, freeze, role changes,
  manual top-up, deployment, repair or customer notification.
