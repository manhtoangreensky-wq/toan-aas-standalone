# Admin Finance Period Read Navigation Design

## Intent

Give canonical administrators a clean Web ERP starting point for the frozen Bot's twelve finite Finance overview, period-summary and export-guidance menus. This is fresh navigation to the existing signed `/admin/finance` read surface, never a transfer of Bot finance data, filter state, command text, export request, file or authority.

## Chosen approach

Extend the existing private `ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS` dictionary with an exact, raw-case-sensitive allowlist. Each literal becomes `NAVIGATION_ONLY`, `admin`, `SIGNED_CANONICAL_ADMIN_READ`, and `WEB_NAVIGATION`; the route independently repeats signed-session and canonical-role checks.

The reviewed literals are:

| Frozen Bot literal | Fresh Web route | Web-native intent |
| --- | --- | --- |
| `menu|finance_overview`, `menu|finance_revenue` | `/admin/finance` | Open a new Finance & Revenue read workspace. |
| `menu|finance_revenue_this_month`, `menu|finance_revenue_last_month`, `menu|finance_revenue_year` | `/admin/finance` | Open the fresh workspace; no Bot period is preselected. |
| `menu|finance_expense_this_month`, `menu|finance_expense_last_month`, `menu|finance_expense_year` | `/admin/finance` | Open the fresh workspace; no expense data or filter crosses the boundary. |
| `menu|finance_profit_this_month`, `menu|finance_profit_year` | `/admin/finance` | Open the fresh workspace; no profit report or period crosses the boundary. |
| `menu|finance_export_month`, `menu|finance_export_year` | `/admin/finance` | Open the fresh workspace only; it does not trigger or prefill an export. |

## Guardrails

The mapping cannot send a Telegram identity/role, ledger/Xu/PayOS/payment data, revenue/expense/profit snapshot, selected period, category, vendor, report argument, command text, export request, file, provider/job state or write authority to the Web App.

`menu|finance_compliance`, `menu|finance_compliance_update`, every `menu|tax_*` value, `menu|finance_revenue_custom_help`, all existing/unknown `menu|finance_*` literals not listed above, case variants and suffixes stay on their current source-review or dedicated-contract boundary. No Bot read query, financial calculation, CSV/file delivery, tax/profile/compliance mutation, wallet/payment/provider action or runtime claim is added.

## Verification

- Assert exactly the twelve new keys plus the 15 existing private Finance registry entries (27 total).
- Assert every reviewed action has a fresh `/admin/finance` target, canonical admin authority, navigation-only status and no-transfer dispositions.
- Assert case variants, suffixes, custom-help, compliance and tax values stay fail-closed.
- Regenerate static evidence from frozen Bot SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
- Run static migration tests, Finance portal contracts, compile/syntax/diff checks, independent review, then PR gate.

## Scope

This changes only static migration evidence and documentation. It does not edit Bot code, Finance runtime/read models, export logic, tax/compliance workflow, bridge, ledger/Xu, PayOS, providers, jobs, video surfaces or LocalVideoStudio26-owned files.
