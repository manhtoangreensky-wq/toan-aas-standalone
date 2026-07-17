# Admin domain centers contract

The standalone Web App exposes five first-class operational areas:

- Operations & Reliability
- Publishing & Channels
- Growth & Affiliate
- Finance & Revenue
- Trends & Reference

`/admin/publishing`, `/admin/growth`, `/admin/finance`, and `/admin/trends`
are protected navigation centers. They organize existing, server-role-protected
Admin routes and clearly retain a read-only/guarded posture when a canonical
Bot adapter has not been published.

## Authority boundary

- The FastAPI signed-session and canonical-admin check remains the only access
  authority. Browser navigation and the catalog never grant an admin role.
- The centers do not call providers, channel APIs, scrapers, PayOS, wallets,
  payouts, referral attribution, publishing automation, or Bot commands.
- They do not add an Admin bridge module or speculate about a Bot endpoint.
  Unsupported routes receive the existing local compatibility guard.
- Finance never maintains a second Xu ledger, payment signer, webhook or
  manual-proof inbox.
- Future write controls require a dedicated canonical adapter, permission,
  CSRF, confirmation, idempotency and audit contract.

The centers are deliberately useful product navigation, but they do not claim
that a Bot command, provider operation, publishing action or financial write
is available from the Web App.
