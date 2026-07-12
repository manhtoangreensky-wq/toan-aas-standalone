# Admin Failed Job Incident Queue

`/admin/jobs/failed` is a role-gated, read-only incident view over the
existing canonical `failed-jobs` bridge module. It is not a second worker
queue, payment ledger, retry controller, or provider console.

The page may show only the bridge's redacted job metadata:

- canonical job ID and feature/type;
- lifecycle status;
- sanitized `error_category`;
- estimated/charged Xu and canonical refund status;
- output-availability signal and update time.

It deliberately does not render a raw exception, provider task/URL, local
path, output/download URL, customer input, Telegram ID, wallet decision, or
PayOS metadata.

There are no retry/refund buttons in this incident view, even if a different
admin route later receives a reviewed write adapter. The Bot remains the
canonical authority for retry eligibility, charges, refunds and provider
operations. A failed incident is therefore triage information only until the
Bot confirms a separate, audited operation.
