# Admin Job Recovery Guide Locale Parity — Design

## Goal

Make the canonical-admin `/admin/job-recovery-guide` readable in the three reviewed interface locales: Vietnamese (`vi`), English (`en`) and Simplified Chinese (`zh`). The surface remains a static, signed, read-only safety guide.

## Product boundary

The guide explains triage and escalation only. It must not read a job, queue, worker, provider, ledger or payment result, and it must not introduce any browser-side clear, retry, refund, charge, delivery, runtime, webhook or provider action. The existing generic canonical-admin server gate, bridge-hydration fence, capability checks, route paths and signed-session protections remain unchanged.

## Chosen approach

Use the same scoped `adminGeneric` locale-catalogue pattern as the already-merged System & Data Stewardship and Postback Readiness pages.

1. Add `adminGeneric.jobRecoveryGuide.*` entries with an identical 39-key set in the `vi`, `en`, and `zh` dictionaries in `static/portal/portal-i18n.js`.
2. Add a tiny `adminJobRecoveryGuideText(key, fallback, params)` wrapper in `static/portal/portal.js` and map only the existing Job-Lock page title to `route.title` / `route.description`.
3. Replace fixed guide text in `renderAdminJobRecoveryGuide` with the wrapper while retaining every Vietnamese string as its fallback and passing interpolated output through `safeText`.
4. Localize the two guide notes at render time and pass localized note labels through the existing backward-compatible `renderNotes(page, labels)` API.
5. Add the three server-side first-paint titles in `_PORTAL_SHELL_TITLES` so the document title is correct before JavaScript finishes loading.

This follows the smallest-safe-change approach. It reuses the existing layout, icons, CSS, responsive behavior, links and status badges; no visual system, motion, navigation or authorization refactor belongs in this scope.

## Locale contract

All languages contain exactly these 39 keys below the `adminGeneric.jobRecoveryGuide` prefix:

- `route.title`, `route.description`
- `intro.kicker`, `intro.title`, `intro.body`, `intro.statusTitle`, `intro.statusBody`
- `checklist.kicker`, `checklist.title`, `checklist.body`
- `checkpoint.triage.title`, `checkpoint.triage.body`
- `checkpoint.evidence.title`, `checkpoint.evidence.body`
- `checkpoint.authority.title`, `checkpoint.authority.body`
- `escalation.kicker`, `escalation.title`, `escalation.body`
- `escalation.itemScope.title`, `escalation.itemScope.body`
- `escalation.itemCanonical.title`, `escalation.itemCanonical.body`
- `escalation.itemEscalate.title`, `escalation.itemEscalate.body`
- `limits.kicker`, `limits.title`, `limits.body`
- `boundary.noMutation.title`, `boundary.noMutation.body`
- `boundary.noRuntime.title`, `boundary.noRuntime.body`
- `boundary.noFinancial.title`, `boundary.noFinancial.body`
- `link.jobs`
- `notes.integration.title`, `notes.safety.title`, `notes.scope.body`, `notes.botBoundary.body`

The Vietnamese fallbacks preserve the current public meaning exactly. English and Chinese clarify that the page is a guidance-only handoff surface; neither language suggests that a browser action can repair a job.

## Rendering and accessibility

Existing semantic headings, list structure, link target and read-only badges are preserved. Every title, body, button label and note is rendered through `safeText`, including localized link text and labels. The route keeps its existing desktop/mobile layout and has no new focus target, form, polling loop or state mutation.

## Failure behavior

If the locale bundle is unavailable or a key is missing, `uiText` returns the explicit Vietnamese fallback already present in the renderer. First-paint server titles similarly use the current server-side locale projection and existing default behavior. Missing data never creates a synthetic job state or fallback action.

## Verification

The new contract test proves catalogue parity, the exact route title and description mapping, three first-paint titles, fallback preservation, safe renderer use, and absence of control-plane code. Existing job-recovery boundary tests continue to prove no request, form, action, queue, job, provider, payment or runtime control is added. Focused pytest, JavaScript syntax checks, migration audit evidence verification and the bounded critical Web App suite are run before PR creation.
