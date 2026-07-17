# Web-native TOTP MFA contract

This module adds an optional second factor to the standalone Web App's
existing Email + password account. It is not a Bot feature and does not change
Telegram identity, Bot tables, Xu, PayOS, provider calls, jobs, assets,
webhooks or Core Bridge authority.

## Enablement

The feature is fail-closed and disabled by default:

```text
WEBAPP_TOTP_MFA_ENABLED=true
WEBAPP_TOTP_MFA_ENCRYPTION_KEY=<URL-safe base64 key decoding to exactly 32 bytes>
```

`WEB_SESSION_SECRET` remains required for the signed Web session. The MFA
encryption key must be a distinct Railway-only secret, never a source value,
browser value, query parameter, log field or test fixture. Startup rejects an
enabled feature with a missing/malformed key.

Keep the flag false in local development and CI unless a dedicated test key is
injected. Do not enable the flag in production as part of this migration task.

## Customer flow

1. A signed Email + password account opens **Tài khoản → Bảo mật tài khoản**.
2. The customer proves the current password to start enrollment.
3. The server returns a one-time manual Base32 setup key to that current tab.
   It expires in 15 minutes and is encrypted at rest before it is persisted.
4. The customer enters a six-digit authenticator code. The server activates
   the factor, consumes that TOTP counter and returns eight recovery codes
   once.
5. On subsequent email/password login, password verification creates only a
   five-minute opaque MFA challenge. No signed session is created until a
   current TOTP code or a one-time recovery code succeeds.
6. Disabling MFA requires the current password, a current authenticator/recovery
   proof, CSRF and explicit confirmation. It invalidates recovery codes and
   rotates signed Web sessions.

The Portal never accepts a raw Telegram ID as an MFA factor. Telegram/OAuth
remain independent sign-in/linking methods.

## Server routes

All responses use the normal envelope shape. The public message is Vietnamese;
the browser must not derive security state from a raw error.

| Route | Session / CSRF | Purpose |
| --- | --- | --- |
| `GET /api/v1/auth/mfa/status` | Signed account | Safe factor posture only; no id, secret, recovery code or token. |
| `POST /api/v1/auth/mfa/enrollment/start` | Signed account + CSRF + current password | Creates one prepared factor and returns the transient setup key. |
| `POST /api/v1/auth/mfa/enrollment/confirm` | Signed account + CSRF | Activates a prepared factor and reveals recovery codes once. |
| `POST /api/v1/auth/mfa/disable` | Signed account + CSRF + password + second factor | Disables factor, invalidates recovery codes and rotates session. |
| `POST /api/v1/auth/login/mfa` | Opaque short-lived challenge | Completes password-first login only after a second-factor proof. |

The startup/route throttle treats login MFA as an authentication credential
endpoint. Enrollment and disable writes are additionally rate-limited and
bound to the current signed session.

## Security invariants

- TOTP secrets use AES-GCM encryption with account/factor-bound associated
  data; database rows never contain the raw secret.
- Recovery codes and opaque enrollment/login tokens are stored only as
  domain-separated HMAC hashes.
- TOTP accepts a bounded clock window but stores the accepted counter to reject
  replay. A recovery code is atomically consumed.
- A new MFA login challenge supersedes old pending challenges; it locks after a
  bounded number of invalid attempts.
- The Portal keeps a setup key, recovery-code reveal and login challenge only
  in live tab memory. They are not put in localStorage, sessionStorage, URL,
  form drafts, service-worker cache or a server-rendered bootstrap.
- Account Security, Browser authorization and all mutation endpoints retain
  server-side ownership and canonical permission checks. Browser capabilities
  only control visible UI.
- If an account has an active MFA factor but runtime/key configuration is
  unavailable, password login fails closed. It never falls back to a
  password-only session.

## Operations and recovery

Do not remove or rotate `WEBAPP_TOTP_MFA_ENCRYPTION_KEY` while active factors
exist. Rotation needs a separate, audited re-encryption migration and is not
part of this release. Disabling `WEBAPP_TOTP_MFA_ENABLED` is not a recovery
shortcut: active factors intentionally remain non-bypassable until an operator
restores the valid runtime/key or follows a separately approved support policy.

Schema changes are additive: `web_totp_factors`,
`web_totp_recovery_codes`, and `web_totp_login_challenges` are Web-owned
tables. They do not migrate or write Bot data.

## Verification

Focused local checks:

```text
python -m pytest -q tests/test_copyfast_mfa.py tests/test_totp_mfa_portal_contracts.py
node --check static/portal/integration.js
node --check static/portal/portal.js
```

The test suite uses mocked/local state only. It must not call Telegram, PayOS,
Key4U, a paid provider or Railway.
