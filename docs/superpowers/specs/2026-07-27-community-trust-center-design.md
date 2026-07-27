# Community & Official Channels Trust Center — Design

## Goal

Replace the `/community` Bot-command handoff with a signed, read-only Web Trust Center. It carries the public, non-sensitive intent of the frozen Bot commands `/official_channels`, `/kenh_chinh_thuc`, `/hub`, `/community`, and `/toanaas_hub` without importing Bot conversation state or giving a browser authority over canonical systems.

## Scope and boundaries

The page presents a small verified directory:

- TOAN AAS website: the reviewed HTTPS public root `https://toanaas.vn`.
- Web Workspace: an internal link to `/dashboard`.
- Telegram Bot: a `t.me/<BOT_USERNAME>` link only when the existing Bot username validation accepts the server configuration.
- Community group: an HTTPS `t.me` invite or channel URL only when `WEBAPP_COMMUNITY_URL` passes the closed validation rules below.
- Support: an internal link to `/support`.

It also presents a localized anti-impersonation checklist: TOAN AAS never asks for a password, OTP, API key, session token, full card number, or payment information through a Telegram message or an unverified link.

The module does not call the Bot, Core Bridge, provider, wallet, PayOS, job, asset, notification, webhook, analytics, or delivery code. It does not create or mutate database records. It accepts no browser-supplied URL, Telegram ID, command, callback, or account data.

## Server contract

`GET /api/v1/community/trust-center` requires the normal signed Web account and returns the account's canonical profile locale only. Request query and `Accept-Language` values never select copy. The response has `Cache-Control: private, no-store`, `Pragma: no-cache`, and `Vary: Cookie`.

The response includes a fresh JSON snapshot with a closed fixed shape: snapshot version, locale, cards, anti-impersonation copy, and false boundary flags. Internal cards use a literal route from the server allowlist. External cards contain a URL only when they are ready. Guarded cards carry a localized explanation and have no `href` value.

`WEBAPP_COMMUNITY_URL` is optional. It is accepted only as an absolute HTTPS URL with hostname exactly `t.me`, no username/password/port/query/fragment, and a non-empty path. Invalid or absent configuration produces a guarded community card rather than a guess, redirect, or hard-coded group link.

`WEBAPP_OFFICIAL_SITE_URL` is optional; its default is the reviewed product root `https://toanaas.vn`. A configured replacement is accepted only as HTTPS with hostname `toanaas.vn` or `www.toanaas.vn`, without credentials, port, query, or fragment. Invalid input guards the website card.

## Client contract

`/community` becomes a `community-trust-center` portal page. The integration layer requests the server snapshot only while the signed session is valid and validates every ID, route, URL, boundary flag, text length, and locale before rendering. A stale, failed, malformed, or signed-out response renders an honest guarded/failed state; it never falls back to a Bot command list or browser-stored URL.

External links always include `target="_blank" rel="noopener noreferrer"`. Guarded cards are non-interactive. The only Bot action is an optional, server-derived, visibly secondary “Mở Bot” link when `BOT_USERNAME` is valid.

The page uses the shared teal–sky tokens, cards, focus treatment, and responsive grid. All new visible strings are available in Vietnamese, English, and Chinese. It respects reduced motion and remains outside the public PWA shell/cache policy.

## Files and ownership

- `copyfast_community_trust.py` owns the frozen safe catalog, config parsing, signed endpoint, and response headers.
- `app.py` mounts only this router.
- `copyfast_registry.py` describes `/community` as the Web-native Trust Center.
- `static/portal/portal.js` owns rendering only.
- `static/portal/integration.js` owns hydration and strict response validation.
- `static/portal/portal-i18n.js` owns all client shell/failure copy.
- `static/portal/portal.css` owns the responsive visual treatment.
- `static/portal/service-worker.js` treats this route/API as private.

## Acceptance criteria

1. An unauthenticated request receives `401`; a signed account sees only its saved locale and fresh no-store data.
2. Valid Bot/community/site configuration produces only closed, HTTPS allowlisted links. Invalid values never reach the browser as a link.
3. The payload has no Telegram identity, command/callback, credential, provider, payment, wallet, job, asset, or bridge field and has all false boundary flags.
4. The portal has explicit loading, guarded, failed, and ready states; external links use `noopener noreferrer`; no raw Bot command is rendered.
5. VI/EN/中文, keyboard focus, desktop/mobile layout, reduced motion, and private PWA treatment are covered by focused tests.
