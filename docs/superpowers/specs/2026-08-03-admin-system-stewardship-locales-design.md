# System & Data Stewardship Locale Design

## Goal

Localize every Portal-owned fixed label on the signed, read-only `/admin/system-stewardship` directory in Vietnamese, English, and Simplified Chinese without changing its data, authorization, or operational boundary.

## Architecture

Add an equal-keyed `adminGeneric.systemStewardship.*` catalog and a narrow `adminSystemStewardshipText()` wrapper. The renderer uses that wrapper for static card copy, markers, guarded/open explanations, manifest explanation, section chrome, and boundary disclosures. The route's navigation label, browser title, description, and first-paint title use the same closed route keys.

## Invariants

- Keep the exact signed Web-admin route guard, `action: "none"`, `status: "read_only"`, card route arrays, local/canonical split, and anchor-versus-guarded-card behavior.
- Keep `adminErpNavigation(context)`, `navigation.groups.length`, `serverAuthorizesAdminRoute(context, card.route)`, `hasLiveCanonicalAdmin(context)`, `badge(state)`, and every `safeText()` boundary semantically unchanged.
- Treat routes, manifest results, capability/authority outcomes, badge states, and any server data as data rather than i18n keys.
- Do not add API/bridge calls, browser storage, forms, actions, POSTs, scheduler/deploy/retry/restore controls, provider/PayOS/wallet/Xu behavior, Bot behavior, CSS changes, or deployment changes.

## User-visible behavior

A signed local Web administrator sees the same directory semantics in all three interface locales. Local cards remain server-guarded; canonical cards remain unavailable without current canonical authority. The directory continues to clearly disclose that it is not a control plane and cannot mutate runtime, provider, payment, or ledger state.

## Verification

Focused static and Node runtime contracts prove equal catalog coverage, route chrome/first-paint localization, preservation of server-controlled card semantics, and absence of browser network/persistence/mutation behavior. The bounded critical Web App suite, syntax checks, evidence verifier, and local signed browser smoke provide release evidence. No live provider, Telegram, PayOS, wallet, or Railway flow is run.
