# Video planning results — local verification, 10/11/2026

Tracker: [Issue #689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).
Contract: [bounded spec](../superpowers/specs/2026-11-10-video-planning-result-locale.md).
BASE: `dac863c9796cc4ef7b077d65579a70300b6d4cc7`.

## Actual scope

The motion-guide result and long-form roadmap result now select fixed interface
copy from their own VI/EN/ZH namespaces. There are 24 motion keys and 45 roadmap
keys. Customer/server titles, topics, style labels, prompts, chapter contents,
captions, calls to action and review lists remain escaped data, not translations.
No compose/save operation, backend authority, capability or source-match rule was
changed. Outer forms, page metadata and the separate save receipt are not covered
by this result-only locale closure.

The coordinator received complete code from two isolated Antigravity sessions,
applied their patches sequentially, and independently verified them. The initial
print requests timed out without usable patches; those attempts are not code
acceptance failures. The same sessions returned complete structured code after
the output format was clarified. No login or global CLI configuration changed.

## Measured evidence

| Gate | Actual result |
|---|---|
| Targeted RED | 45 tests: 21 pass, 24 fail for missing localized result copy/catalog |
| Targeted GREEN | Same unchanged tests: 45 pass, 0 fail |
| Protected Node baseline | 1,924 pass, 0 fail, 211 test files |
| Full Node candidate | 1,969 pass, 0 fail, 212 test files |
| Existing Python source contracts | 24 pass; one historical mobile-nav literal expectation fails identically on BASE and candidate |
| Exact historical failure comparator | Actual test function run against both sources; identical protected section hash `11a9cec68eb1d0b2fe571e378ba131bbef5e3ed6b817113837ec109b4e5f5be5`; 0 new failures |
| Independent localization review | 0 Critical / 0 Important in the two result patches |
| Source preservation | Reverse localization restores both original function bodies; all other portal code is unchanged; removing the two catalog additions restores the original i18n file |
| Existing catalog preservation | All 9,266 prior entries per language and 178 `videoStudioUi` keys remain unchanged |
| Initial native matrix | 24 valid configurations; all locale/data/error checks pass; 18 layout pass, 6 mobile roadmap layout failures |
| Native baseline control | Exact BASE renderer with the same fixture reproduces six overflowing prompt elements |
| Final result matrix | 24/24 pass: two routes, VI/EN/ZH, light/dark, 390/1440px |
| Additional wrap matrix | 24/24 pass: roadmap, VI/EN/ZH, light/dark, 320/414/768/1440px |
| Final aggregate | 48 records, 42 distinct route/locale/theme/width combinations; 0 clipped prompts, page errors, external requests or product writes |

The Node baseline was run with the existing frozen Bot catalog checkout and its
explicit authority SHA. An earlier invocation without that checkout failed setup;
it is not an application regression and is not counted as a passing baseline.

The native runner uses separate temporary accounts per locale, an owned local
server/database/assets, actual current app scripts, real bootstrap normalization
and the public mount entry. One combined run stopped after one valid row on a
heading-readiness timeout; it is preserved as incomplete, not counted as PASS or
an established app defect. The final combined run exposes the existing initial
hydration Promise through a test-only read-only hook and awaits it before
mounting the synthetic result. No app file, hydration behavior, visibility or
error handling is changed by that observer. Results are synthetic, valid planning-only data. No
compose/save action, provider, wallet or production-data operation is exercised.

## Mobile prerequisite, accepted locally

Chapter prompt elements use default `white-space:pre`. At 390px their content is
501px wide in a 280px box. The workspace hides horizontal overflow, so a lack of
page overflow does not make the hidden text readable. A separate worker may add
only a scoped mobile `pre-wrap`/`anywhere` rule, which is now applied. Independent
review confirms exactly that one rule and no other CSS change. The focused
390px test went from six overflowing prompts to zero. In the additional matrix,
12 mobile records preserve the exact 321-character prompt, including two original
newlines and a 300-character unbroken line. At 768/1440px the original `pre` and
`normal` styles remain; desktop fixtures there are 57 characters, not the long
unbroken-string fixture. Mobile controls meet the declared 44px target gate.

## Independent anonymous-access evidence

At the unchanged auth implementation, six routes at 390/1440px produced 12/12
expected outcomes. `/dashboard`, `/features`, `/studio`, `/voice` and `/subdub`
redirect to login with a safe internal return path. `/admin` intentionally returns
JSON 401 under the existing admin policy. Early observers recorded no protected
DOM/visible witnesses. The actual `safeReturnPath` helper passed 22/22 cases.
The 10 login renders keep `main tabindex=-1` and a first-Tab skip link. There were
no JavaScript errors, writes or browser-external requests; the two admin 401
console messages are the expected denials.

This evidence does not cover `/studio/` with a trailing slash, signed hydration,
production login or the complete auth/accessibility requirement.

## Pre-push gate

Operations and original-feature comparison are updated in `TAI-LIEU`.
The independent tester session is
`KIEM-THU/PHIEN-VIDEO-RESULT-LOCALE-20261110.md`; existing tester labels, templates,
Projects metadata and the 48 historical cases are not recreated or overwritten.
The focused 45-case suite is added to the existing CI locale step.

PUSH_GATE=READY.
DEPLOY=NO. LIVE_PASS=NOT_TESTED.
PROVIDER_CALLS=0. WALLET_MUTATIONS=0. PRODUCTION_DATA_MUTATIONS=0.

Whole-app locale, outer video forms, the separately discovered save-receipt
rendering issue, responsive/accessibility coverage, signed lifecycle, final motion
and production/device verification remain in the existing master ledger.
