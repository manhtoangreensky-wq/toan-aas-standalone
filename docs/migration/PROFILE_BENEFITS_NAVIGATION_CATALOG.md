# Profile benefits and pricing navigation catalog

## Purpose

This catalog records the reviewed Profile and Pricing callbacks from the
Telegram Bot baseline and the safe Web behavior for each one. It is an audit
boundary, not a runtime bridge or an entitlement implementation. The Web keeps
its own signed-session and ownership controls; it never accepts a Telegram
callback, package selector, purchase confirmation, referral link, or balance
mutation from a browser.

## Reviewed read navigation

| Bot callback | Fresh Web destination | Canonical authority | Explicit boundary |
| --- | --- | --- | --- |
| `menu|profile_packages` | `/membership` | `CORE_CANONICAL_READ` | Opens an owner-scoped membership overview; it does not reproduce Bot-local package rows. |
| `pricing|main`, `pricing|catalog` | `/pricing` | `SIGNED_CUSTOMER` | Opens the signed Web pricing information surface only; it is not represented as a canonical package or payment read. |
| `pricing|xu` | `/wallet` | `CORE_CANONICAL_READ` | Reads canonical wallet information; no top-up request is created. |
| `pricing|packages`, `pricing|package_summary` | `/packages` | `CORE_CANONICAL_READ` | Opens a guarded canonical package catalog; no package selector or purchase is carried over. |
| `pricing|my_packages`, `pricing|plans`, `pricing|vip`, `pricing|member` | `/membership` | `CORE_CANONICAL_READ` | Opens a fresh tier/benefit summary; no VIP, trial, plan or entitlement is granted. |

The Bot branches above render informational pricing, package, tier, VIP, or Xu
panels. `/wallet`, `/packages`, and `/membership` are
`READ_ONLY_CANONICAL`; `/pricing` is a signed Web information surface because
there is no pricing adapter in this phase. Every page obtains its own signed
context and can be guarded when its adapter is unavailable. The mapping never
proves that a purchase, entitlement, provider job, or payment action completed.

## Telegram-only referral boundary

The following callbacks intentionally remain `TELEGRAM_ONLY`:

- `menu|profile_ref_link`
- `menu|profile_ref_policy`
- `menu|profile_ref_stats`

The Bot derives the referral URL from its Telegram bot identity and reads
referral/reward state that may affect canonical Xu. There is no reviewed Web
`/internal/v1/referrals` adapter in this phase. The Web must not manufacture a
Telegram deep link, render synthetic referral statistics, claim a reward, or
adjust Xu. A future dedicated adapter needs its own signed-owner, anti-replay,
idempotency, audit, and reward-policy review before these callbacks can gain a
Web route.

## Explicitly not included

Promotion redemption, gift codes, birthday updates, package purchase,
confirmation, payment and all `pkgbuy|...` / `buy_plan|...` workflows stay in
their existing Bot/core authority until a separately reviewed Web transaction
contract exists. Video-related pricing paths also remain in the final Video
menu phase.
