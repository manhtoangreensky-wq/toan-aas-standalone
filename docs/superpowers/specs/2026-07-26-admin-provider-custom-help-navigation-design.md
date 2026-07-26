# Admin Provider Custom Help Navigation Design

## Decision

Map exactly one frozen Bot callback, `menu|provider_custom_help`, to the fresh,
signed canonical-admin **read** route `/admin/providers`.

This is static source-disposition evidence only. It does not receive a raw Bot
callback in the browser, accept a provider name, call a provider, run a smoke
test, freeze or unfreeze any provider, expose a secret, import a Telegram
identity, or transfer Bot provider/freeze/worker/payment/Xu/PayOS state.

## Source evidence

The locked Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.

- `bot.py:59133-59145` treats every `provider_custom*` menu action as
  Bot-admin-only before dispatch.
- `bot.py:122202` renders `menu|provider_custom_help` only from the
  administrator Provider Freeze/Queue keyboard.
- `bot.py:122451` resolves the literal to `freeze_action_help_text("provider")`
  and a Telegram-only guidance keyboard. The help text names manual
  `/provider_freeze` and `/provider_unfreeze` commands but does not execute
  either command.

The related `menu|admin_provider_test` action, case variants, and suffixes
remain source-review-required. The existing
`menu|admin_confirm_provider_freeze_*` and
`menu|admin_confirm_provider_unfreeze_shopaikey` callbacks remain
Telegram-only, which is a stricter non-browser boundary.

## Architecture

Add only the literal to the private
`ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` registry in
`scripts/migration/audit_bot_to_web.py`:

```python
{
    "target": "/admin/providers",
    "classification": "admin",
    "feature_key": "admin_providers",
    "authority": "SIGNED_CANONICAL_ADMIN_READ",
    "launch_mode": "WEB_NAVIGATION",
}
```

The existing page route repeats signed canonical-admin authorization. Its
existing API uses `GET /api/v1/admin/providers` and
`require_canonical_admin`; no API, bridge, or UI implementation changes are
required for this slice.

Keep the raw literal private to the static auditor. Do not add it to
`MENU_ACTION_REGISTRY`, `menu_capability_catalog()`, a query parameter, form,
browser event, provider request, or client-side role path.

## Boundary contract

| Source | Target | Authority | Status | Boundary |
| --- | --- | --- | --- | --- |
| `menu|provider_custom_help` | `/admin/providers` | `SIGNED_CANONICAL_ADMIN_READ` | `NAVIGATION_ONLY` | Fresh read navigation only; no provider name/config, command, freeze state, smoke-test state, worker/runtime state, secret, payment/Xu/PayOS/ledger state, or write authority crosses into Web. |

Required dispositions include:

- `BOT_ADMIN_ONLY`
- `BOT_PROVIDER_CUSTOM_HELP_NOT_REPLAYED`
- `FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION`
- `NO_PROVIDER_TEST_FREEZE_UNFREEZE_OR_CONTROL_ACTION`
- `NO_PROVIDER_NAME_OR_CONFIG_TRANSFER`
- `NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION`
- `NO_RUNTIME_CLAIM`

## Generated evidence and validation

The Admin ERP contract count is already derived from its private registry.
Regenerated evidence must show ten exact Admin ERP read navigations, the new
Provider Custom Help row, a menu backlog decrement, updated source-disposition
coverage, and one fewer dashboard-navigation fallback. Its explanatory text
must state that the related test action remains source-review-only and the
existing freeze/unfreeze confirmations remain Telegram-only.

TDD proves the exact lower-case mapping and the current canonical-admin page
gate. It pins the related test action, case variants, and suffixes to the
existing source-review fallback, while confirmation callbacks remain
Telegram-only; neither carries Admin Providers metadata. Static audit runs
against the locked Git baseline into a temporary directory only.

## Out of scope

- Bot edits, raw callback forwarding, Telegram identity transfer, or browser
  admin-role input.
- Provider tests, provider configuration, provider-name input, freeze,
  unfreeze, worker/restart/runtime controls, or secrets.
- PayOS, wallet, Xu, ledger, payment, webhook, job, refund, or deployment
  behavior.
- Video menu work, Railway changes, or live/provider testing.
