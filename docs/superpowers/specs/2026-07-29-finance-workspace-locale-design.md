# Finance Workspace Locale Design

## Intent

Make the Web-owned Finance Operations Planning workspace fully usable in the three reviewed interface locales: Vietnamese, English and Simplified Chinese. This is a presentation-only improvement to the existing signed `/admin/finance/planning` workspace. It must not translate or transform Finance records, server category labels, user-entered notes, amounts, dates, API payloads or any Bot/PayOS/provider data.

## Chosen approach

Keep the existing Portal layout, route, API calls, guards and lifecycle unchanged. Replace only fixed Portal-owned Vietnamese strings inside the Finance Planning renderer and its small formatting helpers with a new `financePlanning.*` namespace in `portal-i18n.js`. Use the existing defensive `uiText` and `localizedNumber` helpers so the browser keeps Vietnamese fallbacks if the catalog is not present, and so number presentation follows the signed Web interface locale rather than a hard-coded `vi-VN` formatter.

The renderer continues to render values supplied by the server exactly as received. In particular, planning category labels, vendor labels, purposes, periods, rows, IDs, revisions and lifecycle values remain data; only their surrounding headings, field labels, buttons, status messages, confirmations and empty-state copy are localized.

## Boundaries

- No new route, API call, storage entry, bridge request, finance calculation, payment, ledger/Xu, PayOS, provider, Bot or export behaviour.
- No locale persistence change; the existing signed profile preference remains the only locale source.
- No translation of user content, server category labels, records, workflow/source languages or Bot text.
- No UI redesign, asset, motion or CSS geometry change. The task preserves the established teal-sky component system and focuses on copy/number presentation.

## Components

1. `static/portal/portal-i18n.js` gains exactly matching `financePlanning.*` keys in `vi`, `en` and `zh` for the fixed Finance Planning UI chrome.
2. `static/portal/portal.js` uses existing `uiText` and `localizedNumber` for Finance Planning labels, confirmations, buttons, empty states and accessibility labels. It maps known lifecycle state tokens to localization keys but preserves unknown values as the existing guarded presentation fallback.
3. `tests/test_finance_planning_portal_contracts.py` gets a static regression contract for the locale helper/use boundaries and proof that planner data is not translated client-side.
4. `tests/test_portal_i18n_bundle_contracts.py` exercises the new key set in all three runtime catalogs and verifies locale-specific Finance Planning output from the browser bundle without importing the app or Bot.

## Error handling and acceptance criteria

- If the i18n bundle is unavailable, `uiText` retains the current Vietnamese fallback and the signed admin workspace still renders.
- Invalid or missing amounts still render as zero using existing safe numeric logic; only grouping follows the chosen interface locale.
- A missing/unknown lifecycle token never becomes a new browser inference and keeps the guarded label.
- All three catalogues expose equal key sets and non-empty reviewed Finance Planning translations.
- `/admin/finance/planning` remains Web-local, signed-admin guarded and has no new bridge, payment, provider, storage or network code.
