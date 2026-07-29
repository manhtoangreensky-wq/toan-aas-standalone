# Admin Finance Workspace Locale Design

## Decision

Localize the fixed interface copy on the signed Admin Finance hub
(`/admin/finance`) and its read-only Tax Readiness guide
(`/admin/finance/tax-readiness`) in the existing Vietnamese, English and
Simplified Chinese Portal catalogues. The signed Web-profile interface locale
remains the only selector; this is not workflow/content translation.

## Scope

- Add one equal-key `adminFinance.*` catalogue per reviewed Portal locale.
- Route Finance-hub headings, stream labels/descriptions, authority notices,
  empty-state copy and boundary text through that catalogue.
- Route all fixed Tax Readiness headings, checklist, handoff and boundary copy
  through that catalogue.
- Keep server data, adapter messages, route names, user-entered values, IDs,
  revisions and state payloads as escaped data rather than translation keys.

## Boundaries

This change does not alter routes, authentication, roles, server manifests,
API clients, Finance Planning storage, Bot integration, Core Bridge, wallet,
Xu, ledger, payment, PayOS, provider, tax calculation, export, files or
runtime behavior. It must not manufacture Finance values or make a browser
action executable merely because its visible copy is localized.

## Implementation shape

`static/portal/portal-i18n.js` gains `ADMIN_FINANCE_WORKSPACE_MESSAGES`, merged
with the existing three reviewed catalogues. `static/portal/portal.js` gains a
small `adminFinanceText` helper, a localized Finance-domain projection, and
localized Tax Readiness literals. The generic Admin-domain renderer receives
localized chrome only for the Finance domain; all other domains retain their
existing copy and behavior.

## Verification

Static Portal contracts prove each locale exposes the reviewed keys, Finance
and Tax Readiness use the helper, and dynamic server values remain escaped.
The focused i18n runtime contract proves equal keysets. JavaScript syntax and
whitespace checks complete the local gate. No Bot audit, provider, PayOS or
production call is run.
