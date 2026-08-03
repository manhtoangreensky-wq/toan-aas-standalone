# Account Center Locale Clarity

## Decision

Localize every fixed, customer-facing string in the existing Account profile/connection overview and Account Activity routes into the reviewed `vi`, `en`, and `zh` catalogues. Retain provider names, server-returned profile values, activity labels, timestamps, IDs, route/action names, and all authorization decisions as data rather than browser translations.

## Scope

- `static/portal/portal-i18n.js`: reviewed `accountCenter.profile.*`, `accountCenter.activity.*`, and Activity page metadata.
- `static/portal/portal.js`: presentation-only key resolution in `renderAccount` and `renderAccountActivity`; localized Activity hero metadata.
- `copyfast_pages.py`: reviewed no-JavaScript Activity title triplet.
- Static contracts for full three-locale key coverage, title mapping, and no new browser authority.

## Explicitly out of scope

- Security/MFA, Data Controls, API/DB/session/CSRF/OAuth behavior, Bot, bridge, provider, wallet, PayOS, payments, and deployment.
- Translating server-owned values or changing any action payload, capability, route, audit boundary, or confirmation semantics.

## Safety invariants

- Browser stays presentation-only: no `fetch`, storage, bridge, payment, provider, or Bot behavior is introduced.
- OAuth/provider identifiers are interpolated as escaped display values only.
- The signed server session remains the source of truth for profile, account connection, and activity data.
