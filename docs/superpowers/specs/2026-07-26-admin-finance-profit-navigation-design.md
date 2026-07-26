# Admin Finance Profit Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_profit`, to the fresh,
signed canonical-admin **read** route `/admin/finance`.

This is static source-disposition evidence only. It does not receive a raw Bot
callback, Telegram identity, finance/profit row, period, report argument,
transaction, Xu/PayOS/payment/ledger state, provider state, or write authority
in the browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` makes every `finance_*` action Bot-admin-only before
  dispatch.
- `bot.py:121504` renders the exact literal on the Bot Finance keyboard.
- `bot.py:121703-121704` defines `finance_profit_menu_text()` as static
  period-selection guidance, without reading finance data or producing a
  profit report.
- `bot.py:122476` dispatches the literal only to that static text and a
  Telegram profit-period keyboard.

The related `menu|finance_profit_this_month` and
`menu|finance_profit_year` values remain source-review-required because they
can read canonical finance data for a chosen period.

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

The target is an existing canonical Admin Finance route. Keep the raw literal
private to the static auditor; do not add it to the public menu catalog, a
browser query parameter, finance form, browser event, bridge method, or
client-side role path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|finance_profit` | `/admin/finance` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot profit data, period/report argument, file/export, payment/Xu/PayOS/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_FINANCE_PROFIT_MENU_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_FINANCE_PERIOD_OR_PROFIT_PARAMETER_TRANSFER`
- `NO_PROFIT_REPORT_OR_FILE_DELIVERY`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is registry-derived. Regenerated evidence must
show thirteen exact Admin ERP read navigations, the new Profit row, one fewer
unresolved menu callback, and no runtime-equivalence claim. The explanatory
contract must keep profit-period/report siblings source-review-only.

TDD proves the exact lower-case mapping, existing canonical-admin page guard,
no public catalog entry, and source-review fallback for profit variants.
Static audit runs only against the locked Git baseline into a temporary
directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Profit data reads, period/report selection, exports/files, finance/tax
  writes, Xu/PayOS/wallet/ledger or payment behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
