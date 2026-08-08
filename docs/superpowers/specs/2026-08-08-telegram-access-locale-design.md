# Telegram and OAuth Access Locale Clarity — Design

## Goal

Make the fixed, customer-visible Telegram one-time sign-in/link and OAuth-provider UI consistently available in Vietnamese, English, and Simplified Chinese. The change improves comprehension of the real secure flow; it does not make a raw Telegram ID valid or add a Bot capability.

## Context

The public access shell already translates email/password copy and optional Telegram onboarding. `renderTelegramLoginMethod`, `renderExpiredTelegramLoginChallenge`, `renderPublicOAuthCard`, and `renderOAuthRegistrationMethods` still contain Vietnamese-only fixed chrome. The authenticated Bot callback protocol deliberately returns server-owned messages, codes, deep links, expiry, and configuration state; browser UI must not translate those values into authority or replace them with invented status.

## Selected approach

Extend the existing `access.*` catalogue in `static/portal/portal-i18n.js` with one closed `access.telegram.*` and `access.provider.*` key set in `vi`, `en`, and `zh`. Reuse the existing `uiText` boundary in `portal.js` for all fixed labels, descriptions, buttons, confirmation prompts, details summaries, and unavailable-provider framing.

For the finite public Telegram error-code catalogue, a presentation-only resolver may choose reviewed local copy from `status` and `error_code`. It does not alter the stored envelope or infer a state: unknown codes and messages still render the escaped server `flow.message` unchanged. The renderer continues to derive the one-time code, expiry, and Telegram deep link from the server result; it never writes them to storage, maps them to an identity, or changes the API routes, callback headers, cookies, CSRF, polling, or redirect behavior.

## User-visible states

| State | Fixed Web copy | Server-owned value retained |
| --- | --- | --- |
| No Telegram challenge | Explanation, action label, independent Web framing | Bot/bridge readiness remains the existing safe server projection |
| Challenge created | Verify title, safe instruction, copy/open/check labels | Code, deep link, expiry and `flow.message` |
| Reloaded pending challenge | Recovery explanation, check/new-code controls and confirmation | HttpOnly challenge state and any signed status message |
| Expired challenge | Expiry framing and new-code action | Escaped expiry message and server error code |
| Telegram account not linked | Account-required explanation and account-entry labels | Escaped server reason and `restart_required` state |
| OAuth provider ready/unavailable | Provider action, description, unavailable framing | Existing server enablement and approved OAuth start URL |

Provider names remain proper names: Telegram Login, Google, GitHub, and Sign in with Apple. Only surrounding explanatory and action copy is localized.

## Boundaries

- No changes to `bot.py`, Bot deployment, Telegram adapter, Bot callback, Core Bridge, PayOS, wallet, providers, jobs, assets, or Railway environment.
- No raw Telegram ID input, browser identity field, localStorage/sessionStorage, token, code persistence, or change to the existing polling lifetime.
- A finite allowlisted error-code resolver may localize only known public protocol states. It retains unknown signed messages as escaped fallback and never changes `status`, `error_code`, data, cookie, session, callback or redirect behavior.
- No fake authentication, OAuth state, linked identity, completion, or provider availability claim.

## Files and responsibilities

- `static/portal/portal-i18n.js` — exact equal `access.telegram.*` and `access.provider.*` key sets for `vi`, `en`, and `zh`.
- `static/portal/portal.js` — fixed-copy translation boundary for the public provider cards and Telegram sign-in presentation; signed protocol values remain unchanged and escaped.
- `static/portal/integration.js` — only the fixed browser-side "challenge is being created" fallback becomes locale-aware, without touching API requests or server-result precedence.
- `tests/test_telegram_access_locale_contracts.py` — locks catalogue parity, renderer use of locale keys, protocol-value preservation, and prohibited raw identity/storage/API changes.

## Verification

1. New focused contract fails before the locale keys/renderer calls exist.
2. Focused locale/auth/onboarding contracts pass after implementation.
3. JavaScript syntax checks pass for the touched browser bundles.
4. A read-only local rendering check at `/login?lang=vi`, `/login?lang=en`, and `/login?lang=zh` confirms fixed auth-alternative copy changes while code/deep-link/message handling stays server-owned.
5. `git diff --check` and migration evidence verification pass. No production, provider, Bot, or Railway flow is run.
