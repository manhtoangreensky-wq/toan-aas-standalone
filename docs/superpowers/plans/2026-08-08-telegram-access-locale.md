# Telegram access and OAuth locale clarity — implementation plan

> **Owner:** Web App only  
> **Branch:** `feature/p0-webapp-telegram-access-locale`  
> **Scope:** customer access presentation in Vietnamese, English, and Simplified Chinese

## Objective

Finish the customer-facing language support for the real Telegram one-time sign-in/link and OAuth entry UI. This is a presentation change only: it must not turn a raw Telegram ID into an identity proof, create a fake sign-in result, or move authority from the signed server/Bot protocol into the browser.

## Implementation order

1. Add one closed `TELEGRAM_ACCESS_MESSAGES` catalogue containing every fixed `access.telegram.*` and `access.provider.*` string in `vi`, `en`, and `zh`, then merge it into the existing equal-keyset catalogue.
2. Replace fixed login/register provider and Telegram wording in `portal.js` with `uiText` through a small presentation helper. Provider names remain proper names; server data stays escaped.
3. Localize only browser-authored fallback notices in `integration.js`. Preserve API routes, zero-argument request bodies, polling, challenge lifetime, cookies, server status, and server-message precedence.
4. Add focused runtime/static contracts: catalogue parity, real Node translation values, renderer usage, server-value escaping and no browser storage/raw identity/API drift.
5. Run focused pytest, JavaScript syntax checks and `git diff --check`, then commit/push/create a separate PR. Merge only after CI is green.

## Non-negotiable protocol boundaries

- The one-time code, deep link, expiry, status, `error_code`, OAuth enablement, callback result, and public server message remain signed protocol values.
- A server message is rendered before a localized fallback and remains escaped with `safeText`.
- Browser code never stores a Telegram ID, code, session credential, OAuth token, or linked identity in local/session storage.
- Telegram login start and completion remain the existing `POST` calls with `{}` bodies. No new provider, wallet, PayOS, job, webhook, or Bot calls are introduced.
- Unknown protocol errors remain server-owned. The UI will not infer a successful link, account, or provider configuration.

## Verification evidence

- `tests/test_telegram_access_locale_contracts.py` executes the browser catalogue in Node and checks all reviewed translations.
- Focused public-auth/onboarding/i18n tests protect the existing signed flow.
- `node --check` validates the two changed browser bundles.
- No live Telegram, PayOS, provider, Bot, or Railway flow is part of this branch.
