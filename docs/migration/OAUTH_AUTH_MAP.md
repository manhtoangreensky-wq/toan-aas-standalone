# Web App OAuth and account-access map

This document covers Web-owned authentication only.  It does not alter
`bot.py`, Telegram identity authority, PayOS, Xu, jobs, provider execution or
webhooks.

## Methods available to a customer

| Method | Current behaviour | Browser trust boundary |
| --- | --- | --- |
| Email + password | Enabled by default; an address ending in `@gmail.com` is treated as a normal email address. | Password is submitted to the same-origin Web API and is scrypt-hashed server-side. |
| Telegram | Passwordless sign-in only after the account was linked through the Bot. | Browser never submits a raw Telegram ID. A one-time Bot proof is bound to an HttpOnly browser challenge. |
| Google OAuth | Disabled unless all Google configuration is present. | OAuth state/PKCE/nonce are server-owned; Google ID token is verified against fixed Google JWKS. |
| GitHub OAuth | Disabled unless all GitHub configuration is present. | OAuth state/PKCE are server-owned; identity comes from fixed GitHub `/user` and verified-email endpoints. |
| Sign in with Apple | Disabled unless Apple Services ID, team/key details and `.p8` private key are present. | Apple form-POST callback uses a dedicated short-lived `SameSite=None; Secure` state cookie; the main signed session remains `Lax`. |

Google/GitHub are deliberately not advertised as active merely because the
page renders a button. The public `GET /api/v1/auth/providers` capability
response controls the UI.

## OAuth configuration (Railway only)

Keep all flags `false` locally and in CI. Never put client secrets, private
keys, access tokens, authorization codes or callback HMAC values in browser
JavaScript, Git, logs or docs.

```text
WEBAPP_PUBLIC_BASE_URL=https://app.toanaas.vn
WEB_OAUTH_IDENTITY_HMAC_SECRET=<long independent random secret>
WEB_COOKIE_SECURE=true

WEBAPP_GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<Google web client id>
GOOGLE_OAUTH_CLIENT_SECRET=<Google web client secret>

WEBAPP_GITHUB_OAUTH_ENABLED=true
GITHUB_OAUTH_CLIENT_ID=<GitHub OAuth app client id>
GITHUB_OAUTH_CLIENT_SECRET=<GitHub OAuth app client secret>

WEBAPP_APPLE_OAUTH_ENABLED=true
APPLE_OAUTH_CLIENT_ID=<Apple Services ID>
APPLE_OAUTH_TEAM_ID=<Apple 10-character Team ID>
APPLE_OAUTH_KEY_ID=<Apple private-key ID>
APPLE_OAUTH_PRIVATE_KEY_BASE64=<base64 AuthKey_*.p8 contents>
```

Register these exact callbacks at the respective provider before turning a
flag on:

```text
https://app.toanaas.vn/api/v1/auth/oauth/google/callback
https://app.toanaas.vn/api/v1/auth/oauth/github/callback
https://app.toanaas.vn/api/v1/auth/oauth/apple/callback
```

The server fails closed at startup if an enabled provider has an invalid base
URL, missing client credential, missing identity-HMAC secret, missing secure
cookie configuration for HTTPS, or (for Google/Apple) no `PyJWT[crypto]`
dependency.

## Security contract

- `state` is high-entropy, stored as a SHA-256 hash, browser-bound by a signed
  HttpOnly cookie, expires in ten minutes, and is consumed before a token
  exchange. Google/GitHub state stays `SameSite=Lax`; Apple uses a dedicated
  short-lived `SameSite=None; Secure` state cookie because Apple returns a
  cross-site form POST. The main signed session always remains `Lax`.
- When secure cookies are active (mandatory for production), session,
  Telegram-challenge and OAuth cookies use `__Host-` names, `Secure`,
  `Path=/`, and no `Domain`. The server does not accept legacy unprefixed
  names in that mode, preventing a sibling subdomain from tossing a competing
  parent-domain cookie. Local HTTP development uses unprefixed cookie names
  only for local testing.
- PKCE is mandatory for Google/GitHub. The verifier and Google nonce are
  derived server-side from the opaque state and an independent HMAC secret;
  neither goes into localStorage.
- Google accepts only RS256 ID tokens with the correct issuer, audience,
  expiry, nonce and verified email. Its immutable `sub`, not email, identifies
  the account.
- GitHub accepts an immutable numeric `/user` ID and a verified email from the
  fixed GitHub API. The requested scope is limited to `read:user user:email`.
- Apple uses `response_mode=form_post`; its token exchange authenticates with
  a freshly generated, five-minute ES256 client-secret JWT signed by the
  Railway-only `.p8` key. Its immutable `sub` is verified against fixed Apple
  JWKS with issuer, audience, expiry and nonce checks. Apple must not create a
  new account when it withholds a verified email, but a previously linked
  Apple `sub` can still sign in without an email response.
- Only an HMAC hash of the external provider subject is retained in
  `web_external_identities`. Access tokens, refresh tokens, ID tokens and raw
  provider subjects are discarded after verification.
- A fresh OAuth identity is never automatically attached to an existing
  email/password account based on matching email. The customer must sign in
  to that existing account and use the CSRF-protected link action.
- Linking binds the OAuth state to the exact signed Web session that started
  it. It cannot change Telegram identity, role, wallet, PayOS, jobs or
  providers.

## Additive Web-only data

`web_oauth_states` holds short-lived hashed state metadata.  It is safe to
delete after expiry/consumption. `web_external_identities` maps a provider and
HMAC-hashed immutable subject to one Web account.  `password_login_enabled`
keeps OAuth-only accounts from accepting the generated unusable local password
hash. These are all additive to the Web session database; no destructive
migration runs and no Bot table is read or written.

## Test boundary

Automated tests mock provider identity fetches; they never contact Google,
GitHub or Apple. Tests cover disabled providers, signed state + PKCE, replay
rejection, Apple form POST, `__Host-` secure-cookie/legacy-cookie rejection,
OAuth-only accounts, subject hashing, no automatic email collision linking,
and CSRF/session-bound explicit linking.
