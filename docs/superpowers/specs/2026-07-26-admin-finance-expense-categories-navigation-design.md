# Admin Finance Expense Categories Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_expense_categories`, to the
fresh, signed canonical-admin **read** route `/admin/finance`.

This is static source-disposition evidence only. It does not receive a raw
Bot callback, Telegram identity, finance row, category value, period,
transaction, wallet/Xu/ledger/PayOS/provider state, or write authority in the
browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` makes every `finance_*` action Bot-admin-only before
  dispatch.
- `bot.py:121532-121538` renders the exact category selector on the Bot
  Finance expense keyboard.
- `bot.py:121743-121747` renders a static sorted list from
  `FINANCE_EXPENSE_CATEGORIES`; it does not query finance records or write an
  expense.
- `bot.py:122471-122482` dispatches the literal only to that static category
  text and a Telegram expense keyboard.

`menu|finance_expense`, period-specific expense callbacks, and
`menu|finance_add_expense` remain source-review-required. They can expose
canonical data, period/category/vendor/note state, or manual write guidance
and must not become browser data/write paths without a separate contract.

## Considered approaches

1. **Fresh canonical-admin Finance read navigation (selected).** The exact
   static category parent opens the existing role-checked Finance view while
   preserving data and write authority boundaries.
2. **Browser expense-category editor.** Rejected: it would mutate canonical
   finance configuration or expenses and is outside this static guidance
   slice.
3. **Leave the parent unresolved.** Safe but does not capture the existing
   static-only Bot category guidance for the Web parity inventory.

## Architecture

Add only the literal to the private
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` registry with target
`/admin/finance`, `SIGNED_CANONICAL_ADMIN_READ`, and `WEB_NAVIGATION`.

The target already uses canonical server-side authorization. Keep the raw
literal private to the static auditor; do not add it to the public menu
catalog, a browser query parameter, expense form, browser event, bridge
method, or client-side role path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|finance_expense_categories` | `/admin/finance` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot finance data, period/category input, expense write, file/delivery, payment/Xu/PayOS/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_FINANCE_EXPENSE_CATEGORIES_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_FINANCE_PERIOD_OR_EXPENSE_PARAMETER_TRANSFER`
- `NO_EXPENSE_WRITE_CATEGORY_OR_FILE_DELIVERY`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is registry-derived. Regenerated evidence must
show fifteen exact Admin ERP read navigations, the new Categories row, one
fewer unresolved menu callback, and no runtime-equivalence claim. The
explanatory contract must keep data, period, write, and variant callbacks
source-review-only.

TDD proves the exact lower-case mapping, existing canonical-admin page guard,
no public catalog entry, and source-review fallback for the sensitive siblings
and variants. The static audit runs only against the locked Git baseline into a
temporary directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Finance data reads, period/category/vendor/note input, expense writes,
  report/export/file delivery, Xu/PayOS/wallet/ledger or payment behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
