# Job Support Recovery Contract

The Job Detail page may offer a customer support form only when the
owner-scoped canonical job has status `failed`, `failed_no_charge`,
`cancelled`, or `guarded`. It may also offer a **delivery-pending** form when
the canonical job is `completed`, output metadata is reported, and neither
the matching owner-scoped asset nor the job has a `delivery_ready=true`
artifact.

- The ticket subject contains the validated Job ID so the support team can
  compare it manually inside the Bot support workflow.
- The Web form sends only `subject` and customer-written `detail` through the
  existing signed-session, CSRF and idempotent ticket route.
- It does not send a hidden `job_id`, create `related_job_id`, retry a job,
  refund Xu, attach an asset, reveal a provider/output URL, or expose PayOS
  data. The current Bot bridge accepts only text ticket fields, so it remains
  the source of truth for any future canonical job-ticket relationship.
- A delivery-pending ticket says only that delivery is still pending. The
  Portal does not mint a URL, retry delivery, infer a file, or turn a
  completed engine status into a successful Web download.
- Server and client ticket validation continue to reject secrets, card/OTP
  data and manual-payment bill/TXID/account/QR evidence.

This is a recovery handoff, not an engine or financial action.
