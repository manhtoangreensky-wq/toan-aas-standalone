# Admin Billing Pending Navigation Design

## Decision

Map exactly one frozen Telegram callback, `menu|admin_billing_pending`, to a
fresh, signed canonical-admin **read** route: `/admin/payments`.

This is source-disposition evidence only. It does not receive a raw Bot
callback in the browser, forward a Telegram identity, query a pending bill by
ID, create a payment, approve/reject a bill, credit Xu, finalize PayOS, test a
provider, register a webhook, or create a second ledger.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
At `bot.py:122385-122399`, `menu|admin_billing_pending` only renders the
parameter-free help text “Dùng `/pending` để xem bill thủ công đang chờ.” The
same static menu also contains `admin_billing_duyet`, `admin_billing_tuchoi`,
and `admin_billing_payos`, whose help texts point to commands that approve,
reject, or test a payment workflow. Those three remain source-review-required.

`handle_menu_callback` treats `admin_*` actions as Bot-admin-only before the
page dispatcher is reached, but it also clears Bot-local pending/session state.
The Web mapping begins a new signed session and never replays that state.

## Architecture

Add the literal to the private, case-sensitive
`BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS` registry in
`scripts/migration/audit_bot_to_web.py`. The existing `_map_callback` billing
path already looks up the exact identifier and emits fresh canonical-admin
navigation. No public `menu_capability_catalog()` entry is added.

The target route uses `GET /api/v1/admin/payments` with
`require_canonical_admin` and an `admin_read=True` bridge request. It is a
canonical-read projection, never a browser payment control.

## Contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|admin_billing_pending` | `/admin/payments` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no Bot bill ID, deposit, payment reference, Xu ledger, PayOS/webhook, provider, job, runtime, or write authority crosses into Web. |

Only this exact lowercase literal is allowed in addition to the reviewed parent
`menu|billing`. Case variants, suffixes, `menu|admin_billing_duyet`,
`menu|admin_billing_tuchoi`, and `menu|admin_billing_payos` must have neither
the Admin Payments route nor `NAVIGATION_ONLY` status.

## Generated evidence and validation

The static audit generator derives the billing-contract row count from its
private registry, renders the pending row, and states that approve/reject/PayOS
test siblings stay source-review-only. TDD asserts the exact mapping, negative
siblings, no public catalog exposure, no-transfer dispositions, and generated
contract output. The audit runs statically against the locked Git baseline; no
Bot process, provider, PayOS, Telegram, database, or Railway flow runs.

## Out of scope

- Bot source edits or raw callback forwarding.
- Payment approval/rejection, PayOS test, webhook, ledger, Xu, refund, top-up,
  package, provider, job, or runtime actions.
- New browser forms, payment APIs, deployment, or live testing.
