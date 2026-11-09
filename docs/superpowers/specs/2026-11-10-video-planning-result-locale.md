# Video planning result locale — 10/11/2026

TRACKING_ISSUE: #689, manhtoangreensky-wq/toan-aas-standalone.
BASE_SHA: dac863c9796cc4ef7b077d65579a70300b6d4cc7.
Worker source snapshot: 2df134eb6731195e5bbff938215afd3202f385b1;
the two allowed application files are byte-equivalent at these revisions.

This is the next bounded unit in the existing R218 completion ledger, not a
replacement for the whole-app, authentication, responsive or final-motion gates.
The Owner requires fixed Vietnamese UI to be Vietnamese, fixed English UI to be
English, and fixed Chinese UI to be Chinese. Brands and customer/server text are
not translated.

## Ordered units

| Spec | Result | Dependency | Delivery |
|---|---|---|---|
| RESULT-LOCALE-VIDEO-PLANNING-MOTION | Localize the motion-guide result chrome in VI/EN/ZH | Valid renderer fixtures and immutable source packet | Local accepted |
| RESULT-LOCALE-VIDEO-PLANNING-ROADMAP | Localize the long-form roadmap result chrome in VI/EN/ZH | Valid renderer fixtures and immutable source packet | Local accepted |
| RESULT-LOCALE-VIDEO-PLANNING-ROADMAP-WRAP | Wrap chapter prompt text on mobile without changing its content | Native baseline/candidate reproduced the same six overflowing prompts | Local accepted |
| RESULT-LOCALE-VIDEO-PLANNING-VERIFY | Verify both results, protected data, guards and regression | Both worker patches independently reviewed | Local accepted |
| RESULT-LOCALE-VIDEO-PLANNING-DELIVERY | CI, merge, deploy, runtime and asset verification | All local gates and pre-push review | Pending |

The two builders return text-only patches in isolated packets. They cannot edit
the repository. The coordinator applies patches sequentially and independently
verifies each result. No application repair by the coordinator before two
same-acceptance code failures through Antigravity.

## Locked scope

- `static/portal/portal.js`: only `renderCreativeMotionGuideResult` and
  `renderLongFormRoadmapResult`; signatures, guards, dynamic expressions and
  actions remain unchanged.
- `static/portal/portal-i18n.js`: add `videoMotionResultUi` and
  `videoRoadmapResultUi`; preserve every existing dictionary entry, including all
  178 `videoStudioUi` keys.
- `tests/video-planning-result-locale.test.mjs`: independent renderer coverage.
- `.github/workflows/webapp-quality.yml`: add this focused Node test to the
  existing locale-regression step; do not change jobs, permissions or deployment.
- `static/portal/portal-theme.css`: one media rule at `max-width:620px`, scoped
  to the existing long-form chapter prompt hierarchy; only `white-space:pre-wrap`
  and `overflow-wrap:anywhere`. Desktop, forms and other routes stay unchanged.
- This spec, operational evidence and provenance metadata may be updated for
  verified delivery; no unrelated application files.

Protected: customer/server titles, topics, style labels, prompts, body text,
caption, calls to action and review lists; identifiers, numbers, platform codes,
ratios, URLs, action names, capability checks, source matching, normalizers,
session/CSRF authority, backend, engine, Bot, provider and money logic.

## Acceptance checklist

- [x] AC-01: Real normalized fixtures reach selected/custom/no-result motion
  states and empty/populated roadmap states; invalid fixtures cannot substitute
  for rendered-result evidence.
- [x] AC-02: Every approved fixed label, fallback, helper, stale notice and save
  confirmation inside the two result renderers uses exact VI/EN/ZH copy.
- [x] AC-03: Customer/server sentinels and raw payloads remain unchanged;
  source-match, save action, route and disabled guards remain intact.
- [x] AC-04: Existing dictionary entries and unrelated application bytes are
  unchanged. No new controls, blank containers or success/readiness claims.
- [x] AC-05: Targeted renderer and Python contracts, syntax checks and full Node
  regression have actual successful terminal output.
- [x] AC-06: Owned isolated browser renders mobile/desktop in VI/EN/ZH, with no
  page errors, unintended writes, external requests, clipping or page overflow.
- [ ] AC-07: Review, tester evidence and provenance are ready before push; CI,
  merge, deployment, runtime SHA and live asset checks are separate evidence.

PROVIDER_CALLS=0. WALLET_MUTATIONS=0. PRODUCTION_DATA_MUTATIONS=0.
No ENV, credentials, schema, login/settings or paid-provider changes.

Authentication cold-route audit runs independently without application writes.
Final whole-app motion remains the last implementation group in the master ledger.

## Native prerequisite found during verification

The first 24-configuration native run passed all locale/data/guard/error checks,
but six mobile roadmap configurations each exposed six overflowing prompts:
`scrollWidth=501`, `clientWidth=280`, `white-space:pre`, `overflow-wrap:normal`.
The enclosing workspace hides horizontal overflow. A control serving exact BASE
JavaScript with the same valid fixture reproduced the same six prompt overflows.
This is a pre-existing display defect, not a translation regression. It remains
was kept open until the scoped CSS worker patch and native rerun passed; page-level overflow
being false is not accepted as proof that these prompt contents are readable.

Local acceptance evidence: 45/45 targeted, 1,969/1,969 full Node; Python 24 pass
with one proven historical BASE-equivalent failure; independent reviews show
0 Critical/Important; native 24/24 result and 24/24 additional-wrap records.
The bounded report records the incomplete diagnostic runs and observer limit.
