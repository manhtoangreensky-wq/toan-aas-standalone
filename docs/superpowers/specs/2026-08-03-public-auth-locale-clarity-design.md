# Public Auth Locale Clarity Design

## Purpose

Make the public Web account entry routes read naturally in Vietnamese, English
and Simplified Chinese without changing authentication, account ownership or
any canonical Bot-managed business state.

## Approved scope

This is the narrow continuation of merged PR #283. The existing public access
locale selector remains the only presentation input and it accepts only `vi`,
`en` and `zh`.

The change localizes the remaining immediate static copy that a visitor sees
on `/login`, `/register` and `/password-recovery`:

- password-recovery heading, introduction, primary title, description,
  submit label and field label/help;
- the successful-registration handoff notice on `/login?registered=1`;
- the OAuth result notice on `/login?oauth=...`;
- the default-profile notice on `/register`;
- the shell document title for `/password-recovery` before JavaScript loads.

`/password-recovery` also receives a recovery-specific context headline so it
does not inherit registration language.

## Presentation architecture

`static/portal/portal-i18n.js` remains the single browser-copy source. New
keys are added exactly once to each of its existing `vi`, `en` and `zh`
bundles. `static/portal/portal.js` continues to resolve those keys through
`uiText` / `accessText`; it does not add storage, requests or auth state.

The recovery email field is metadata only. It receives `labelKey`,
`placeholderKey`, and `helpKey`, just like the login and registration fields,
so the existing field renderer projects reviewed locale text. The form action
stays `auth-password-recovery-start` and the generic non-enumerating backend
response remains unchanged.

`copyfast_pages.py` gains only the `vi`/`en`/`zh` title tuple for
`/password-recovery`. The existing allowlisted request locale resolver and
render path are deliberately reused. During local route QA, the renderer
correctly received the public path from `app.py` but rejected it because the
closed `copyfast_registry.allowed_paths()` set omitted it. Add the one explicit
recovery path there; do not add a broad public prefix or weaken the renderer's
unknown-route 404 boundary.

The selected public locale also remains present across the two presentation
continuations that leave the initial page: registration's handoff to `/login`
and OAuth's signed return state. Only `vi`, `en` and `zh` may be retained; the
OAuth return-path validator still strips every other query value, provider
response and external target. This does not add a cookie, OAuth configuration,
session field or redirect authority.

## Exact behavior that must remain unchanged

| Route | Existing action | Required preservation |
| --- | --- | --- |
| `/login` | `auth-login` | Email/password, OAuth and Telegram behavior stay unchanged. |
| `/register` | `auth-register` | Registration response, password policy and server session behavior stay unchanged. |
| `/password-recovery` | `auth-password-recovery-start` | The form remains public, no-transient, and returns a generic response that does not disclose whether an email exists. |

No raw Telegram ID may be added to browser inputs, copy or storage. This PR
does not touch OAuth provider configuration, Telegram linking challenges,
MFA, CSRF, sessions, rate limits, password recovery transport, Core Bridge,
PayOS, wallet/Xu, providers, jobs, webhooks, Bot code or Railway.

## Explicit deferrals

Dynamic Telegram connection/challenge/status text is intentionally deferred.
It crosses account and onboarding state and needs a separate, state-aware
locale contract. Provider-card copy and the general security-help disclosure
are also outside this focused follow-up; they retain their current behavior.

## Validation design

A new static contract test locks:

1. every new `access.*` key occurs exactly three times;
2. recovery field metadata, route and action remain correct;
3. `renderAuth` uses locale keys for every scope item above;
4. the recovery shell title exists in all three server locales;
5. the declared public recovery path renders the English shell with HTTP 200;
6. the access presenter cannot gain browser API, storage, payment, provider,
   wallet or raw Telegram-ID behavior by accident.
7. registration and OAuth can carry only the reviewed `vi`/`en`/`zh` locale
   through their existing public continuation paths.

Focused Python tests, JavaScript syntax validation, public route rendering at
desktop and 375px mobile, and the frozen migration evidence gate are run
before the PR is opened.
