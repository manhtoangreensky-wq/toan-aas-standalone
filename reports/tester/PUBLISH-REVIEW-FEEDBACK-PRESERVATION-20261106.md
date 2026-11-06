# Tester session PUBLISH-REVIEW-FEEDBACK-PRESERVATION-20261106

STATUS=LOCAL_ACCEPTED_PENDING_EXACT_HEAD_CI_DEPLOY_AND_SIGNED_LIVE
PRODUCT=TOAN AAS standalone WebApp
REPO=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=5aa0683c72b79445e525d8c33c4dd0eecf8934eb
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md
CASE_IDS=PR-FEEDBACK-06,PR-FEEDBACK-07,PR-FEEDBACK-08

## Measured evidence

- Baseline 42 message cases: 21 passed, 21 failed (12 unknown-message content,
  three Vietnamese jargon cases, six actual-native fixed-message cases).
- After Antigravity's two exact scoped patches: 42/42 feedback cases, 119/119
  combined targeted Node, 1,523/1,523 indexed Node, all with zero failures.
- Python/native/shell/contracts: 10/10; includes native temporary-DB API envelope
  through actual integration bundle and toast in VI/EN/ZH, preserving receipt.
- Syntax checks of both changed application bundles passed.
- Independent source/index review: Critical 0, Important 0, Minor 0; reviewer
  reran 42/42 feedback tests and compared 70-key sets and all 68 old EN values.
- Tester metadata suite: 32 passed, one unchanged Windows POSIX file-mode failure
  (0666 versus 0600); no skip, xfail, chmod or test weakening. Linux CI is required.

## Scope and limitations

Only the feedback map/helper block in `integration.js` and feedback catalog rows
in `portal-i18n.js` changed. Seven fixed messages map to 70 balanced keys per
locale; old English values remain unchanged. Unknown nonempty messages, including
prototype-like strings, retain displayed content. Currentness, validators, all
callers, generic catch, APIs, auth/CSRF, backend, schema, Bot, provider, wallet,
PayOS and motion remain unchanged. Provider calls, wallet and production-data
mutations are zero. Calendar's two untracked preflight files are excluded.

This follow-up corrects the previous session's unsupported blanket statement that
unknown messages were already preserved. The original 77 tests did not cover the
missing behavior. No synthetic QA, HTTP200, merge or deployment proves signed
production UI or real external publication. Independent review, exact-head CI,
runtime revision and signed UI observation are separate release gates.
