# Admin Finance Revenue Month Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_revenue_month`, to the
fresh, signed canonical-admin **read** route `/admin/finance`.

This is static source-disposition evidence only. It does not receive a raw Bot
callback, finance period, report argument, revenue value, transaction, ledger
row, Xu/PayOS/payment state, export request, or a Telegram identity in the
browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` treats every `finance_*` menu action as Bot-admin-only
  before dispatch.
- `bot.py:121503` renders the exact literal only on the Bot Finance keyboard.
- `bot.py:121689-121695` defines `finance_revenue_month_menu_text()` as
  static period-selection command guidance.
- `bot.py:122466` dispatches the literal to that static text and a Telegram
  period keyboard. It does not calculate or deliver a report itself.

The related `menu|finance_revenue`,
`menu|finance_revenue_this_month`, `menu|finance_revenue_last_month`,
`menu|finance_revenue_year`, `menu|finance_revenue_custom_help`, and
`menu|finance_export*` values remain source-review-required because they can
read canonical finance data, accept a period, or begin export guidance.

## Architecture

Add only the literal to the private
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` registry:

```python
{
    "target": "/admin/finance",
    "classification": "admin",
    "feature_key": "admin_finance",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
}
```

The target is already an existing canonical Admin Finance route. Keep the raw
literal private to the static auditor; do not add it to a public catalog, query
parameter, finance form, browser event, bridge method, or client-side role
path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|finance_revenue_month` | `/admin/finance` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot finance data, period/report argument, export request, file, payment/Xu/PayOS/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_FINANCE_REVENUE_PERIOD_MENU_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_FINANCE_PERIOD_OR_REPORT_PARAMETER_TRANSFER`
- `NO_REPORT_EXPORT_OR_FILE_DELIVERY`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is registry-derived. Regenerated evidence must
show eleven exact Admin ERP read navigations, the new Finance Revenue Month
row, one fewer unresolved menu callback, and no runtime-equivalence claim.
The explanatory contract must keep finance data/period/export siblings
source-review-only.

TDD proves the exact lower-case mapping, target page authorization, no public
catalog entry, and source-review fallback for finance/report variants. Static
audit runs only against the locked Git baseline into a temporary directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Finance data/revenue calculations, period input, reports, exports/files,
  expense writes, tax configuration, Xu/PayOS/wallet/ledger/payment behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
