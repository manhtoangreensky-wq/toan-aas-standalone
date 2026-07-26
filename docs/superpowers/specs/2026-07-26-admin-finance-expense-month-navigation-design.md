# Admin Finance Expense Month Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_expense_month`, to the
fresh, signed canonical-admin **read** route `/admin/finance`.

This is static source-disposition evidence only. It does not receive a raw Bot
callback, Telegram identity, finance/expense row, period, category, vendor,
note, report argument, export request, transaction, Xu/PayOS/payment/ledger
state, provider state, or write authority in the browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` makes every `finance_*` action Bot-admin-only before
  dispatch.
- `bot.py:121503` renders the exact literal on the Bot Finance keyboard.
- `bot.py:121697-121701` defines `finance_expense_month_menu_text()` as
  static period-selection/add-expense guidance, without reading finance data or
  writing an expense.
- `bot.py:122471` dispatches the literal only to that static text and a
  Telegram expense-period keyboard.

The related `menu|finance_expense`, `menu|finance_expense_this_month`,
`menu|finance_expense_last_month`, `menu|finance_expense_year`,
`menu|finance_expense_categories`, and `menu|finance_add_expense` values
remain source-review-required because they can read finance data, enumerate
categories, select a period, or describe an expense-write command.

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
| `menu|finance_expense_month` | `/admin/finance` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot expense data, period/category/vendor/note, expense-write command, report/export/file, payment/Xu/PayOS/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_FINANCE_EXPENSE_MONTH_MENU_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_FINANCE_PERIOD_OR_EXPENSE_PARAMETER_TRANSFER`
- `NO_EXPENSE_WRITE_CATEGORY_OR_FILE_DELIVERY`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is registry-derived. Regenerated evidence must
show twelve exact Admin ERP read navigations, the new Expense Month row, one
fewer unresolved menu callback, and no runtime-equivalence claim. The
explanatory contract must keep expense data, period/category/add-expense, and
export siblings source-review-only.

TDD proves the exact lower-case mapping, existing canonical-admin page guard,
no public catalog entry, and source-review fallback for expense variants.
Static audit runs only against the locked Git baseline into a temporary
directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Expense data reads, period/category selection, vendor/note input, expense
  writes, reports, exports/files, tax configuration, Xu/PayOS/wallet/ledger or
  payment behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
