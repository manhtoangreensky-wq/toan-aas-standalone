# Admin Package Catalog Navigation Design

## Decision

Map exactly one frozen Telegram callback, `menu|admin_packages_catalog`, to a
fresh, signed Web Admin Packages **read** route: `/admin/packages`.

This is a source-disposition change only. It does not create a browser callback
endpoint, a new public capability, an API, a package grant/revoke action, a
customer entitlement view, a payment action, or a Bot change.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
At `bot.py:122413-122446`, the package admin keyboard defines four child
actions, and all four render static command guidance at
`bot.py:122420-122425`. `admin_packages_catalog` is the only child that directs
to the read-only `/package_catalog` command. The adjacent `grant_combo`,
`grant_monthly`, and `user` texts guide privileged grant or user-lookup
operations. They remain fail-closed: the callback itself carries no parameter,
but it must not imply a Web package mutation or lookup capability.

## Alternatives considered

1. Add a broad menu-to-route fallback. Rejected: the existing migration audit
   intentionally fails closed for raw Bot menu values, and a keyword fallback
   could turn privileged or financial callbacks into browser actions.
2. Build package mutation controls or a Bot bridge. Rejected: Bot remains the
   canonical package/wallet/payment authority and this slice must not introduce
   a second writer.
3. Add one private exact-source disposition to the existing canonical-admin
   navigation registry. Selected: it matches the already-reviewed
   `menu|admin_packages` parent route while preserving every sensitive child
   boundary.

## Architecture

`scripts/migration/audit_bot_to_web.py` keeps the source-only allow-list in
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS`. The auditor already looks up that
registry by the original, case-sensitive identifier before all generic menu
fallbacks. Adding the single literal therefore produces a
`NAVIGATION_ONLY` audit record with the existing `admin_packages` feature key,
canonical-admin authority, and `/admin/packages` destination.

The registry remains private to the static auditor. `copyfast_registry.py`'s
browser-safe `menu_capability_catalog()` must not gain an admin route or a raw
Telegram callback identifier.

## Contract

| Source | Target | Audience | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|admin_packages_catalog` | `/admin/packages` | canonical signed admin | `NAVIGATION_ONLY` | Fresh read navigation only; no Telegram identity/menu context, package code, user ID, grant/revoke/adjustment, entitlement, Xu, PayOS, provider, job, runtime, or write authority crosses into Web. |

Only the literal above is permitted. Case variants, suffixes, and the adjacent
`menu|admin_packages_grant_combo`, `menu|admin_packages_grant_monthly`, and
`menu|admin_packages_user` callbacks stay outside the allow-list and retain
their current source-review status.

## Validation

Focused migration tests will first assert the exact mapping and public-catalog
non-exposure, then fail before the registry entry exists. After implementation,
they must prove the exact token maps to `/admin/packages` as canonical-admin
read navigation while case variants, suffixes, and mutation/user child actions
have neither that route nor `NAVIGATION_ONLY` status. The static audit report will be regenerated from the
locked Bot Git snapshot; no Bot code or provider/payment/live flow is run.

## Out of scope

- Any Bot source edit or Telegram callback forwarding.
- Package grant, revoke, adjustment, user lookup, entitlement, wallet/Xu,
  PayOS, provider, job, runtime, or audit-log write behavior.
- UI redesign, new browser controls, deployment, Railway, provider, payment,
  or live Telegram testing.
