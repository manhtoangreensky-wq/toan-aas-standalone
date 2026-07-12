# Telegram Bot ↔ Web App connection

Entering a Telegram ID in a browser is not an authentication method: another
person can know or guess that value. The Web App therefore uses the existing
Bot bridge rather than trusting an ID field.

## Two real connection paths

Telegram Login OIDC establishes a signed Web session directly at Telegram and
does not require changing bot.py. The existing Bot one-time link then proves
the canonical identity that owns Xu, PayOS state, jobs and private assets.

For an account created by Telegram Login OIDC, the Bot callback must prove the
same Telegram user before canonical data unlocks. The comparison is performed
server-side on HMAC-protected identity material; neither raw ID is rendered in
the browser.

### Telegram Login OIDC setup (Web-only)

In BotFather, open Bot Settings, then Web Login, and register both Allowed
URLs:

    https://app.toanaas.vn
    https://app.toanaas.vn/api/v1/auth/oauth/telegram/callback

Store the Client ID and Client Secret that BotFather gives you only in the Web
App Railway service:

    WEBAPP_TELEGRAM_OAUTH_ENABLED=true
    TELEGRAM_OAUTH_CLIENT_ID=<BotFather Web Login client id>
    TELEGRAM_OAUTH_CLIENT_SECRET=<BotFather Web Login client secret>
    WEBAPP_PUBLIC_BASE_URL=https://app.toanaas.vn
    WEB_OAUTH_IDENTITY_HMAC_SECRET=<long independent random secret>
    WEB_COOKIE_SECURE=true

This uses server-side OIDC authorization code plus PKCE and fixed-JWKS RS256
verification. It does not use a Telegram Bot token, change a Telegram
webhook, touch PayOS, or alter bot.py. Keep the enabled flag false until the
Allowed URLs and Railway secrets are ready; the Web UI remains honestly
disabled rather than creating a dead button.

```text
Web signed session
  → create one-time code (10 minutes)
  → https://t.me/<BOT_USERNAME>?start=web_<code>
  → Bot sees the real Telegram caller
  → Bot POSTs signed callback to Web
  → Web records Bot proof as pending for the initiating browser
  → same signed browser session completes with CSRF
  → Web binds identity / creates Telegram-first Web account
  → browser exchanges its bound challenge for a signed session
```

The separately audited Bot bridge source contains both `/start web_<code>`
and `/linkweb <code>`, which call `confirm_web_link_from_telegram`. No
wallet, PayOS webhook, Xu mutation, provider call, or browser-supplied
Telegram ID is involved in this flow.

## Current source-boundary warning

The requested frozen Bot baseline is
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`. The local bridge worktree
currently audited by the migration report is
`32d6d1bfbc8040b0632a44e6a9326ed568cb1a59`, six commits ahead of that
baseline, where the private callback adapter was added. This document does
**not** claim that this adapter is in the currently deployed Bot.

Because the Web-only scope must not change `bot.py`, do not enable the
deep-link callback in production merely by setting the Web variables below.
It becomes a live identity link only after an explicitly approved Bot bridge
deployment/configuration uses the matching callback contract. Until then,
Telegram Login OIDC may create a signed **Web** session, but canonical Bot
wallet/jobs/assets correctly remain locked rather than accepting a raw ID or
pretending the link succeeded.

The Web defaults `WEBAPP_TELEGRAM_BOT_LINK_ENABLED=false`. This is a
non-secret release gate: set it to `true` **only after** the paired Bot adapter
has been deployed with the callback URL and matching secrets below. It does
not claim the Bot is healthy; the first valid signed callback is still the
end-to-end proof. With the gate off, Portal explains that the Bot adapter is
pending and refuses to mint a code which the Bot would not understand.
It also rejects a signed callback for an in-flight code without consuming that
code, so the flag is a real maintenance stop rather than a presentation-only
toggle.

## Required paired Railway configuration

Set the same random values in the **Bot** service and the **Web App** service;
do not put them in Git or browser JavaScript.

| Service | Variable | Value / purpose |
| --- | --- | --- |
| Web App | `BOT_USERNAME` | Public Bot username, without `@`; enables the deep link. |
| Web App | `WEBAPP_LINK_CALLBACK_TOKEN` | Random shared bearer token for the Bot → Web callback. |
| Web App | `WEBAPP_LINK_CALLBACK_HMAC_SECRET` | Independent random shared HMAC secret for the exact callback body. |
| Web App | `WEBAPP_TELEGRAM_BOT_LINK_ENABLED` | `true` only after the paired Bot callback adapter is deployed and configured; defaults to `false`. |
| Bot | `WEBAPP_LINK_CALLBACK_URL` | `https://app.toanaas.vn/api/v1/auth/internal/telegram-link/confirm` |
| Bot | `WEBAPP_LINK_CALLBACK_TOKEN` | Exactly the same value as the Web App. |
| Bot | `WEBAPP_LINK_CALLBACK_HMAC_SECRET` | Exactly the same value as the Web App. |

The Web App refuses to mint a login or account-link code until all four Web
settings above are present and the explicit Bot-adapter release gate is true.
This avoids a button that looks active but can only create a dead code.
`BOT_USERNAME` and the release gate are non-secret; the token and HMAC secret
are Railway secrets. The two callback credentials must not fall back to, or
reuse, any `CORE_BRIDGE_*` credential.

`/api/v1/auth/telegram/connection/status` distinguishes two honest states:

- **Web ready**: the Web receiver has its public Bot username and dedicated
  callback secrets, so it can safely mint a one-time deep link.
- **Bot callback observed**: Web has accepted at least one signed Bot callback
  after deployment. It exposes only a safe callback kind and timestamp, never
  the customer, Telegram ID, code, request ID, or secret.

The endpoint cannot read the Bot's Railway variables or prove the Bot is
currently online. The first successful one-time callback is the end-to-end
proof. If the Bot replies that it cannot confirm a code, check the Bot
variables in the table rather than asking the customer to type a Telegram ID
again.

For Portal data after linking, configure the separate private core bridge
pair, also as Railway secrets:

```text
Web App: CORE_BRIDGE_BASE_URL=<private Bot HTTPS URL>
Web App: CORE_BRIDGE_TOKEN=<shared core bearer token>
Web App: CORE_BRIDGE_HMAC_SECRET=<shared core HMAC secret>
Bot:     CORE_BRIDGE_TOKEN=<same core bearer token>
Bot:     CORE_BRIDGE_HMAC_SECRET=<same core HMAC secret>
```

The link callback secret and the core-bridge secret are separate directional
credentials. Never reuse a PayOS key, Bot token, provider key, or browser
session secret for either one.

The callback is limited to a small JSON body, rate-gated before application
processing, and parsed only after its dedicated bearer/HMAC check. Its HMAC
binds the exact body, HTTP method, path, timestamp and callback request ID.
The persistent callback nonce is retained through the full accepted timestamp
window, including permitted clock skew. Audit records use that authenticated
callback request ID, never an unrelated browser request-id header.

## Safe deployment handoff

1. Generate one random callback token and one independent random HMAC secret
   in the Railway secret UI; do not paste either value into code, a ticket, or
   browser DevTools.
2. Put the token/secret in the matching Web and Bot variables in the table
   above, and set the Bot callback URL exactly to the Web endpoint.
3. Set the public `BOT_USERNAME` on the Web service, then restart both
   services through the normal deployment process.
4. Open `GET /api/v1/auth/telegram/connection/status` on the Web service. It
   reports only readiness booleans and the names of missing variables. A
   `completed` response means the Web can issue a deep link and verify a
   signed callback; it intentionally does not claim the remote Bot is online.

No PayOS webhook, wallet ledger, provider key, Telegram Bot token, or browser
credential is shared in this handoff.

## Persistence prerequisite

The Web-only database holds signed sessions, CSRF tokens, one-time link/login
code hashes and callback replay nonces. It is **not** a Bot wallet/job/PayOS
database, but it must survive a normal deploy/restart. Production startup now
fails closed unless either:

```text
WEBAPP_SESSION_DB_PATH=/data/toanaas_webapp_session.db
```

points to a persistent Railway volume, or a persistent `/data` mount exists.
Use an absolute path for `WEBAPP_SESSION_DB_PATH`; do not rely on the project
working directory or an ephemeral container filesystem.

## Returning to the requested workflow

When a signed Web account reaches a customer workflow before its Telegram
identity is linked, the Portal preserves the intended **local** route as an
onboarding continuation. After the Bot proves the identity, the Portal returns
the user to that workflow instead of always sending them to Dashboard.

The continuation accepts only a plain same-origin path. It rejects absolute
URLs, protocol-relative paths, query/fragment values, backslashes and
login/register/onboarding loops. It never carries a Telegram ID, payment,
provider URL or secret.

Google, GitHub and Apple OAuth starts pass the same validated local path into
the signed OAuth state. If OAuth creates an account that still needs Telegram,
the callback sends it through the safe onboarding continuation as well.

## User behaviour

- First Telegram sign-in now creates a minimal Web-only account only after
  signed Bot proof. It has default profile `vi`, `Asia/Ho_Chi_Minh`, gradient
  avatar, and Telegram sign-in; no raw Telegram ID is rendered to the browser.
- A Telegram-first account can later add an unused Email + password from its
  signed Account page. This upgrades the same Web account; it never silently
  merges it with a separate email/OAuth account that happens to exist.
- After the customer starts a one-time login/link challenge, the same visible
  browser tab checks only its own short-lived challenge status. Login uses an
  HttpOnly browser token; account linking is additionally bound to the exact
  signed session that created the code. Returning from Telegram therefore
  resumes automatically; the manual **Kiểm tra ngay** button remains a
  fallback. A refreshed tab never restores the opaque code, deep link or a
  Telegram identity from localStorage; it receives only pending or
  ready-to-complete state for its own session. A Bot callback alone never
  mutates a Web account: the initiating browser must make the CSRF-protected
  completion request. Polling stops when hidden, expired, rejected or
  completed.
- Existing Email, Google, GitHub, and Apple accounts can continue to link a
  Telegram identity via onboarding. A Telegram identity cannot attach to two
  Web accounts or replace an existing linked identity.
- The Web endpoint `/api/v1/auth/telegram/connection/status` exposes only safe
  readiness booleans and missing variable names, never values or remote Bot
  secrets.
- The Portal provides a **Sao chép lệnh** fallback (`/linkweb <one-time-code>`)
  when a mobile/browser cannot open the Telegram deep link. The command holds
  only a short-lived opaque code; the Bot still proves the caller identity.
- Public PWA shell assets are network-first with offline fallback, so an
  installed app refreshes the current login/link UI after deploy. Private API,
  wallet, payment, admin and file responses remain outside the cache policy.

## Verification without production side effects

1. On Web, select **Đăng nhập với Telegram** and open the generated deep link.
2. In Bot, `/start web_<code>` (or `/linkweb <code>`) invokes the signed
   callback adapter. The current reference Bot may show its legacy success
   text; the customer must still return to the same Web tab for completion.
3. Return to the same browser tab. The Portal should detect the signed
   callback and make the session-bound CSRF completion automatically;
   **Kiểm tra ngay** is a manual fallback. The signed session must appear
   without exposing a raw Telegram ID.
4. Try the same code again, a different browser/session, changed input, an
   expired code, or a callback after logout: each must be rejected.

The recommended callback URL has no trailing slash:

```text
https://app.toanaas.vn/api/v1/auth/internal/telegram-link/confirm
```

The Web App also accepts the slash-suffixed form so an existing Bot environment
does not fail through a redirect; both forms are HMAC-bound to their exact path.

This task does not set Railway secrets, deploy either service, or call a live
Telegram/PayOS/provider endpoint.
