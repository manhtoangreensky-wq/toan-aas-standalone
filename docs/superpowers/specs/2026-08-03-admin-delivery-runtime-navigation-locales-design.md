# Admin Delivery & Runtime Navigation Locale Parity — Design

## Goal

Localize the fixed Delivery & Runtime area of the signed canonical Admin ERP in Vietnamese (`vi`), English (`en`), and Simplified Chinese (`zh`). The work covers server-authorized navigation chrome, page hero title/description, and server first-paint document title for the exact nine existing routes.

## Exact route allowlist

- `/admin/jobs`
- `/admin/jobs/failed`
- `/admin/job-recovery-guide`
- `/admin/providers`
- `/admin/provider-cost`
- `/admin/workers`
- `/admin/features`
- `/admin/freezes`
- `/admin/runtime`

The exact server-issued group ID is `delivery_runtime`. No other canonical group, dynamic module, support desk, provider record, job record, command, bridge response, payment, worker state, or server authority is translated by this change.

## Safety boundary

`adminErpNavigation(context)` remains a server-authorized projection. It must continue to validate the source `read_state`, group/modules, canonical routes, availability/state and authority exactly as it does today. Localization is a presentation projection applied only after those values have been admitted and only for the closed allowlist above. It must not add routes, make a guarded route visible, cache metadata, call an API, read browser storage, set an action, or manufacture a job/provider/payment/runtime status.

The existing Job-Lock Recovery guide keeps its dedicated locale namespace. Its navigation label and description reuse those reviewed keys instead of creating a second translation of safety-sensitive copy.

## Chosen architecture

1. Add `adminGeneric.deliveryRuntimeNavigation.*` keys for the Delivery & Runtime group plus the eight non-Job-Recovery routes in `portal-i18n.js`. Use the existing `adminGeneric.jobRecoveryGuide.route.*` keys for the ninth route.
2. Add one closed route map in `portal.js`. It maps only the exact paths above to reviewed title/description locale keys. A separate closed group map resolves only `delivery_runtime` title/description.
3. Add a small presentation helper that returns `uiText(key, fallback)` only when the route/group is in the allowlist. Unknown server metadata retains its server-provided fallback verbatim.
4. Apply the helper inside `adminErpNavigation` after route validation. This makes desktop navigation, mobile navigation, command palette, Admin directory, and module cards consistently use the reviewed locale without changing their routes or capability state.
5. Add exact-path branches to `localizedPageTitle` and `localizedPageDescription`, and first-paint titles in `copyfast_pages.py`.

## Copy contract

The group receives `group.title` and `group.description`. Each of the eight new route identifiers receives `title` and `description`:

- `jobs`
- `failedJobs`
- `providers`
- `providerCost`
- `workers`
- `features`
- `freezes`
- `runtime`

All three dictionaries have the same 18 keys. Vietnamese fallbacks exactly preserve the existing `adminPage` title/description strings. English and Chinese describe only read-only status/metadata and retain the no-control boundary. The Job Recovery route reuses its existing 39-key namespace and does not change its renderer.

## First paint and fallback behavior

Each exact path gets a locale-aware document title in `_PORTAL_SHELL_TITLES`. If the browser catalogue is absent, the already-existing Vietnamese literals remain the visible fallback. Unknown group IDs/routes remain untouched and cannot receive a guessed translation.

## Verification

The RED contract proves all three language keysets are equal and non-empty, exact route/group maps are closed, route validation and state/authority projection are preserved, and no control-plane tokens are added. It validates each localized route hero and first-paint title. Existing Job Recovery contracts continue to guard the dedicated safety route. Focused pytest, JavaScript syntax, `compileall`, migration evidence verification, and the bounded CI critical suite run before the PR is merged.
