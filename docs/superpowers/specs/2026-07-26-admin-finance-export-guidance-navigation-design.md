# Admin Finance Export Guidance Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_export`, to the fresh,
signed canonical-admin **read** route `/admin/finance`.

This is static source-disposition evidence only. It does not receive a raw Bot
callback, Telegram identity, finance/export row, period, command argument,
file request, transaction, Xu/PayOS/payment/ledger state, provider state, or
write authority in the browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` makes every `finance_*` action Bot-admin-only before
  dispatch.
- `bot.py:121504` renders the exact literal on the Bot Finance keyboard.
- `bot.py:121706-121712` defines `finance_export_menu_text()` as static
  command guidance and explicitly says the Telegram callback only shows
  guidance to avoid sending a file by mistake.
- `bot.py:122479` dispatches the literal only to that static text and a
  Telegram export-period keyboard.

The related `menu|finance_export_month` and `menu|finance_export_year` values
remain source-review-required because they describe a period-specific export
command and must never become a browser file/export action without a separate
owner-scoped canonical delivery contract.

## Architecture

Add only the literal to the private
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` registry with target
`/admin/finance`, `SIGNED_CANONICAL_ADMIN_READ`, and `WEB_NAVIGATION`.

The target is an existing canonical Admin Finance route. Keep the raw literal
private to the static auditor; do not add it to the public menu catalog, a
browser query parameter, finance form, browser event, bridge method, or
client-side role path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|finance_export` | `/admin/finance` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot finance data, export period/command, file/delivery, payment/Xu/PayOS/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_FINANCE_EXPORT_GUIDANCE_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_FINANCE_EXPORT_PERIOD_OR_COMMAND_TRANSFER`
- `NO_REPORT_EXPORT_OR_FILE_DELIVERY`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is registry-derived. Regenerated evidence must
show fourteen exact Admin ERP read navigations, the new Export Guidance row,
one fewer unresolved menu callback, and no runtime-equivalence claim. The
explanatory contract must keep export-period siblings source-review-only.

TDD proves the exact lower-case mapping, existing canonical-admin page guard,
no public catalog entry, and source-review fallback for export variants.
Static audit runs only against the locked Git baseline into a temporary
directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Finance data reads, export period/command input, report generation,
  file/delivery, tax writes, Xu/PayOS/wallet/ledger or payment behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
