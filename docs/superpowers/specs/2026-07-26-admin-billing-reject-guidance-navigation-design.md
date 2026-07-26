# Admin Billing Reject Guidance Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|admin_billing_tuchoi`, to the
fresh, signed canonical-admin **read** route `/admin/payments`.

This is static source-disposition evidence only. It does not receive a raw
Bot callback, Telegram identity, pending-deposit or bill ID, payment
reference, transaction, wallet/Xu/ledger/PayOS/webhook/provider state, or
write authority in the browser.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59128-59148` applies the Bot-admin check to every `billing*` and
  `finance*` action before dispatch.
- `bot.py:122385-122390` renders the exact Billing keyboard literal.
- `bot.py:122392-122399` defines the `tuchoi` page as static manual-command
  guidance: an operator uses `/tuchoi <bill_id>` only after real-money
  reconciliation; no rejection happens from this menu callback.
- `bot.py:122434-122441` dispatches the literal only to that static guidance
  and a Telegram back keyboard.

`menu|admin_billing_payos` remains source-review-required because it describes
PayOS test commands and must not become a browser payment, test, webhook, or
ledger action without a separate canonical contract. The previously reviewed
Approval Guidance parent remains a separate exact, read-only disposition.

## Considered approaches

1. **Fresh canonical-admin Payments read navigation (selected).** The exact
   guidance parent opens the existing role-checked view while preserving all
   financial authority boundaries.
2. **Browser rejection form.** Rejected: it would require an idempotent,
   canonical payment/ledger authority and is outside this static guidance
   slice.
3. **Leave the parent unresolved.** Safe but does not capture the existing
   static-only Bot guidance for the Web parity inventory.

## Architecture

Add only the literal to the private
`BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS` registry with target
`/admin/payments`, `SIGNED_CANONICAL_ADMIN_READ`, and `WEB_NAVIGATION`.

The target already uses canonical server-side authorization. Keep the raw
literal private to the static auditor; do not add it to the public menu
catalog, a browser query parameter, Billing form, browser event, bridge
method, or client-side role path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|admin_billing_tuchoi` | `/admin/payments` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot bill/payment data, manual command, approval/rejection, PayOS test/webhook, wallet/Xu/ledger/provider/runtime state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_BILLING_REJECT_HELP_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_BILL_ID_OR_PAYMENT_REFERENCE_TRANSFER`
- `NO_PAYMENT_APPROVE_REJECT_PAYOS_TEST_OR_WEBHOOK_ACTION`
- `NO_PAYOS_WALLET_OR_LEDGER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Billing contract count is registry-derived. Regenerated evidence must show
four exact Billing read navigations, the new Rejection Guidance row, one fewer
unresolved menu callback, and no runtime-equivalence claim. The explanatory
contract must keep PayOS test, case variants, suffixes, and future callbacks
source-review-only.

TDD proves the exact lower-case mapping, existing canonical-admin page guard,
no public catalog entry, and source-review fallback for the sensitive sibling
and variants. The static audit runs only against the locked Git baseline into a
temporary directory.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Bill review/approval/rejection, manual top-up/TXID, payment creation,
  payment/order lookup, PayOS test/finalization/webhook, Xu/wallet/ledger or
  refund behavior.
- Provider calls, jobs, runtime controls, Railway changes, live testing, or
  any Video-menu work.
