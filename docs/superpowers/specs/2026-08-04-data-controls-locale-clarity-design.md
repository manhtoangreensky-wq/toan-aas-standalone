# Data Controls Locale Clarity Design

## Goal

Make the signed Web-only Data Control Center understandable in Vietnamese,
English, and Chinese without changing what data it can read, export, request
for review, or cancel.

## Chosen approach

Use one fixed-copy `accountCenter.dataControls.*` catalogue in the existing
Portal i18n bundle and a small `dataControlsText(key, fallback, params)`
presentation helper. The renderer and browser-only action messages resolve
only reviewed fixed keys through that helper. Server data remains canonical:
category keys, request state keys, counts, timestamps, request IDs, revisions,
server `result.message`, policy version, scope key, acknowledgement literals,
and capability flags are never translated, reformatted, persisted, or sent
back differently.

This is preferred to route-specific copied strings because it follows the
Account Security locale boundary, keeps all translations auditable in one
catalogue, and cannot create a second privacy-policy implementation in the
browser.

## Scope

- Localize the Data Controls route title, description, first-paint server title,
  guarded/loading/empty states, category labels, fixed request-state labels,
  explanatory copy, form labels, confirmations, disabled help, and browser
  fallback toasts/errors.
- Preserve every existing route, form name, `data-portal-action`, endpoint,
  request method/body/header, CSRF requirement, idempotency key, expected
  revision, confirmation acknowledgement literal, and server-message priority.
- Keep `WEBAPP_DATA_CONTROLS_ENABLED` default-off and all PWA private-cache
  exclusions unchanged.

## Explicit non-goals

- No Bot, Telegram, Core Bridge, wallet, PayOS, provider, job, asset, support,
  database, auth, or deletion-policy change.
- No translation of signed-account data or of `REQUEST WEB AUTHORING ERASURE`
  and `CANCEL WEB ERASURE REQUEST`, which are canonical request payloads.
- No new endpoint, export job, automatic deletion, background task, browser
  storage, or provider notification.

## Safety and verification

The static contracts must prove a three-locale equal-key set, escaped dynamic
values, preserved request shapes, fixed browser-only fallback localization,
and first-paint metadata. Focused Data Controls/auth/i18n tests, JavaScript
syntax checks, private-route smoke QA, and the existing static migration audit
provide the acceptance evidence.
