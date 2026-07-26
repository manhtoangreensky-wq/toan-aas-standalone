# Admin Finance Add-Expense Planning Entry Design

## Decision

Map exactly one frozen Bot callback, `menu|finance_add_expense`, to the
fresh, signed **Web-local-admin** Finance Operations Planning entry at
`/admin/finance/planning`.

This is static source-disposition evidence only. It never forwards the raw Bot
callback, Telegram identity or Bot-admin role to a browser. It does not create,
pre-fill, approve or archive a Web plan. The separately owned Finance Planning
route starts empty and applies its own signed-session, feature-gate, CSRF,
confirmation, idempotency, revision and audit rules only when an authenticated
Web-local admin deliberately uses it.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` makes every `finance_*` action Bot-admin-only before
  dispatch.
- `bot.py:121505` and `bot.py:121535` render the literal on two Telegram
  expense keyboards.
- `bot.py:121714` resolves the literal to `finance_add_expense_help_text()`;
  it presents `/expense_add` and `/expense_add_pre` guidance and explicitly
  says the button does not automatically record an expense.
- The separate admin-only commands later write canonical
  `finance_expense_events`; they are not this callback and remain out of
  scope.

That Bot help/action boundary is not portable. The Web target is an
independently designed, prospective operating-cost-plan workbench, not a
continuation of Telegram help, commands, pending input or a canonical expense
write.

## Considered approaches

1. **Fresh Web-native Finance Planning entry (selected).** Reuses the existing
   `/admin/finance/planning` route without transferring Bot state. It gives a
   privileged Web operator a modern, independently governed place to start an
   operating-cost plan.
2. **Canonical `/admin/finance` read navigation.** Rejected: the Bot literal
   is help for separate write commands; a generic financial read screen would
   neither express the intended fresh-start boundary nor preserve the local
   planning lifecycle.
3. **Keep the literal source-review-only.** Safest but leaves a reviewed,
   independently safe Web-native entry undiscoverable in the parity inventory.

## Architecture

Add only the literal to a dedicated private
`FINANCE_ADD_EXPENSE_FRESH_WEB_PLANNING_ACTIONS` registry with:

```text
target: /admin/finance/planning
classification: admin
feature_key: admin_finance_planning
authority: SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING
launch_mode: WEB_NAVIGATION
```

The registry and mapper are intentionally separate from
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS`, whose members are canonical-admin
read navigations. The Bot action does not grant or prove a canonical role, and
the target's server-side `require_admin` gate does not promote a signed Web
admin into a Bot admin. No public capability catalog, query parameter, bridge
call, browser event, form-prefill, payment control or client-side role path may
contain the raw callback.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|finance_add_expense` | `/admin/finance/planning` | `SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING` | `NAVIGATION_ONLY` | Fresh empty Web-native planning entry only; no Bot help, command, pending state, expense ID, amount, period, category, vendor, note, pre-establishment, finance row, ledger/payment/wallet/Xu/PayOS/provider/job state or write authority transfers. |

Required source dispositions include:

- `BOT_ADMIN_ONLY`
- `FRESH_SIGNED_WEB_LOCAL_ADMIN_FINANCE_PLANNING_NAVIGATION`
- `BOT_FINANCE_ADD_EXPENSE_HELP_NOT_REPLAYED`
- `BOT_MENU_CALLBACK_CONTEXT_NOT_REPLAYED`
- `BOT_PENDING_SESSION_STATE_NOT_REPLAYED`
- `NO_BROWSER_NAVIGATION_HISTORY_OR_RESET_ACTION`
- `NO_BOT_EXPENSE_COMMAND_OR_FINANCE_EXPENSE_EVENT_TRANSFER`
- `NO_CANONICAL_FINANCE_DATA_TRANSFER`
- `NO_BOT_EXPENSE_ID_AMOUNT_CATEGORY_VENDOR_NOTE_OR_PRE_ESTABLISHMENT_TRANSFER`
- `NO_PAYMENT_PROOF_OR_FINANCIAL_IDENTIFIER_TRANSFER`
- `NO_PAYOS_WALLET_XU_LEDGER_PROVIDER_OR_EXPORT_ACTION`
- `NO_RUNTIME_CLAIM`

`menu|finance_expense`, all period selectors, category-child values, case
variants, suffixes and future `menu|finance_add_expense*` values remain
source-review-required. The already reviewed static
`menu|finance_expense_categories` parent retains its existing separate
canonical-read navigation; it does not inherit the Planning route. No other
callback can inherit this route.

## Validation

TDD must prove the exact lower-case literal gains only this target and local
planning authority; it must prove the target does not become a public catalog
entry, and all sensitive siblings/variants fail closed. Existing Finance
Planning contract tests continue to pin the server-side signed-local-admin
route and its independent payment/ledger boundary.

Regenerate the static audit against the locked Bot baseline into a temporary
directory. Curate only the generated Finance Add-Expense contract, migration
index and semantic parity documentation. Do not modify Bot files, bridge code,
PayOS/webhook/ledger paths, provider code, Railway configuration or visible
portal UI in this slice.

## Out of scope

- Bot edits, raw callback forwarding, Telegram linking or Bot-state migration.
- Canonical expense reads/writes, financial data transfer, ledger/Xu/wallet,
  PayOS/payment/webhook, refund, tax, report/export or file delivery.
- New Finance Planning fields, UI redesign, client-side prefill, provider/job
  action, live testing, Railway deployment or Video-menu work.
