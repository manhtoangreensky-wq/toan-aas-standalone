# Web Password Recovery Contract

## Scope

This is a Web-native password recovery flow for an active account that already
has an Email + password login factor. It is separate from email-link
assurance, Telegram identity, Bot state, Core Bridge, Xu, PayOS, providers,
jobs, assets, files and publishing.

It never merges accounts, reclaims a Telegram/OAuth identity, changes a
canonical Bot identity or creates a signed session. Telegram-first and
OAuth-only internal aliases cannot enter this flow.

## Enablement

The capability is off by default. It needs an explicit flag plus the same
authenticated SMTP transport and public origin used by the optional mailbox
assurance adapter:

    WEBAPP_PASSWORD_RECOVERY_ENABLED=true
    WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL=https://app.toanaas.vn
    WEBAPP_EMAIL_SMTP_HOST=...
    WEBAPP_EMAIL_SMTP_PORT=587
    WEBAPP_EMAIL_SMTP_USERNAME=...
    WEBAPP_EMAIL_SMTP_PASSWORD=...
    WEBAPP_EMAIL_SMTP_TLS_MODE=starttls
    WEBAPP_EMAIL_VERIFICATION_FROM=no-reply@...

WEBAPP_EMAIL_VERIFICATION_ENABLED is independent; an operator can enable
recovery without enabling signed-account mailbox assurance. If the recovery
flag is enabled with an incomplete SMTP/public-origin configuration, normal
application startup fails closed. With the flag off, the public endpoint
returns the same generic acknowledgement and sends nothing.

## Flow

1. A visitor submits an email at POST /api/v1/auth/password-recovery/start.
   The public response is identical for known, unknown, disabled, non-password
   and rate-limited identities.
2. For an eligible account, the server stores a prepared, short-lived
   challenge with only an HMAC digest of a random token, superseding older
   active recovery challenges for that account.
3. SMTP handoff is queued after the browser response and outside the SQLite
   lock. Only a successful handoff can mark the challenge sent; a failure is
   recorded as failed and cannot reset a password.
4. Opening the emailed URL only renders a no-store form. A preview or mail
   scanner cannot consume the proof.
5. Manual form submission validates the HMAC, state, expiry, account/email
   match and password policy. It consumes the exact proof, sets the password,
   revokes every active Web session, supersedes other recovery challenges and
   clears the submitting browser cookie. No replacement session is minted.

The confirmation URL is one-time, expires by default after 20 minutes and
requires a new password different from the old one. A replay or invalid link
only receives a no-store invalid-link page.

## Data and audit

web_password_recovery_challenges is an additive Web-only table. It keeps the
account-local email, HMAC token digest, lifecycle timestamps and no raw token.
It has no wallet, payment, provider, Bot, job or asset data. Audit events
retain fixed action/outcome metadata only; SMTP exceptions, recipient values
and secrets are not placed in browser responses or audit detail.

## Browser and PWA boundary

/password-recovery is a public Portal page with no transient form retention.
It receives no token, account state, delivery status or email verification
result. The confirmation page is server-rendered with no-store, no-referrer
and a restrictive CSP. The service worker has no recovery navigation fallback
and never caches confirmation/API responses.

## Verification

Focused tests cover generic public responses, SMTP fake delivery, HMAC-only
storage, scanner-safe GET, manual confirmation, mismatch retry, replay
rejection, session revocation, old/new password login and per-account limits.
No live SMTP, Bot, provider, PayOS, wallet or job call is made.
