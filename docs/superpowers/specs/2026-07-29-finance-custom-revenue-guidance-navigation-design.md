# Finance Custom Revenue Guidance Navigation Design

## Decision

Map exactly one frozen Bot callback, menu|finance_revenue_custom_help, to a
fresh signed canonical-admin /admin/finance navigation. The Web destination is
an entry point only; it never replays the Bot custom-period instruction, period
selector, revenue snapshot, command, report, export or Finance state.

## Source evidence

At frozen baseline b29d0d474974075f4cba963d2c510f49d2d1b3e4, the callback
returns finance_revenue_month_menu_text plus the static revenue period keyboard.
The selector contains a separate custom-month action, but this callback itself
does not accept a period or create a Bot write.

## Boundary

The exact lower-case literal remains NAVIGATION_ONLY with
SIGNED_CANONICAL_ADMIN_READ. Case variants, suffixes, custom period input,
report/export callbacks, tax/compliance actions and every other unlisted
menu|finance_* value remain fail-closed. No Bot identity, selected period,
command text, snapshot, ledger/Xu, PayOS/payment, provider, file/export,
calculation, write or runtime authority transfers to Web.

## Scope

Only the private static auditor, focused migration contracts and generated
migration evidence change. No Web route, UI, API, Bot source, bridge, wallet,
PayOS, provider or Finance runtime changes.

## Verification

A failing exact-key contract proves the new entry exists while case/suffix
variants remain source-review-required. Regenerate static evidence, then run
focused migration tests, Python syntax and whitespace checks.
