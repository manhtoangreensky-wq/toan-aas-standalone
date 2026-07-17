# Web Email Verification Contract

## Scope

This is a Web-owned mailbox assurance feature for a signed account with an
active Email + password login factor. It is independent from Telegram
identity, Bot state, Core Bridge, Xu, PayOS, provider execution, jobs, files,
assets, publishing and delivery.

It proves only that a user who can access a mailbox completed a fresh
one-time link. It does not reset a password, recover an account, expose an
email address to another account, merge identities, change a canonical
Telegram identity or make an external payment/provider call.

Registration remains non-enumerating and does not auto-send a link. Sending
only after a signed-account request avoids making account existence observable
through SMTP delivery timing; a new password account can sign in and request
its own proof from Account Security.

## Enablement

The feature is disabled by default. A deploy may enable it only after these
server-side values are configured:

    WEBAPP_EMAIL_VERIFICATION_ENABLED=true
    WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL=https://app.toanaas.vn
    WEBAPP_EMAIL_SMTP_HOST=...
    WEBAPP_EMAIL_SMTP_PORT=587
    WEBAPP_EMAIL_SMTP_USERNAME=...
    WEBAPP_EMAIL_SMTP_PASSWORD=...
    WEBAPP_EMAIL_SMTP_TLS_MODE=starttls
    WEBAPP_EMAIL_VERIFICATION_FROM=no-reply@...

TLS mode is either starttls or ssl. Incomplete configuration fails closed:
the customer sees a guarded state and no link is minted or claimed as sent.
Secrets never appear in API responses, Portal state, audit detail, links,
browser storage or tests.

## Flow

1. A signed account requests a link from Account Security with CSRF and
   explicit confirmation.
2. The server rechecks the active session and password factor inside its
   transaction, rate-limits the account, invalidates older active challenges,
   and stores only an HMAC digest of a newly random token.
3. SMTP delivery runs outside the database lock over authenticated TLS. The
   challenge becomes usable only after the handoff succeeds.
4. Opening the link renders a no-store interstitial; it does not consume the
   challenge, so a mail scanner or preview cannot verify it accidentally.
5. The customer manually submits the interstitial. The server validates the
   state, expiry, HMAC, current account email and active password factor,
   records the Web email-link contact, consumes the challenge and supersedes
   the account's other active challenges.

The link is short-lived, single-use, does not create a session, and remains
safe to replay: a replay shows an invalid-link page without changing data.

## Data and audit

The additive Web-only tables are:

- web_account_email_contacts: account-local verified email, method and times;
- web_email_verification_challenges: account-local email, HMAC token digest,
  lifecycle and times.

Neither table stores a raw token, SMTP credential, provider token, Bot ID,
payment data, job state or file/output reference. Audit records retain only
fixed action/outcome metadata.

## Portal and PWA

The Portal fetches only the owner-scoped assurance state, delivery
availability and pending flag. It never retains a mailbox token, contact email
from a provider or SMTP configuration. Account Security is private, and the
service worker does not cache API responses or confirmation pages.

## Verification

Focused tests cover CSRF, disabled/incomplete configuration, delivery failure,
rate limits, absent raw tokens in API responses, manual confirmation,
scanner-safe GET rendering, one-time replay rejection, current-login-email
matching and sanitized audit/data boundaries. SMTP is replaced by an
in-process fake in tests; no email is sent.
