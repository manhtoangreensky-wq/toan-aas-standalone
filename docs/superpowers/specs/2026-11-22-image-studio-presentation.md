# IMAGE-STUDIO-PRESENTATION-20261122

GOAL: readable customer copy, no redundant explanation cards, full-width create
form and readable light-theme detail counts. BASE:
`07a89b79c442981ecb7433b607c981740c95c774`; tracker Issue689/comment7075958364.

Application allowlist: `static/portal/portal.js`, `portal-i18n.js`,
`portal-theme.css`. Twenty-three exact reviewed records:
CREATECOPY9 + DETAILCOPY R2 10 + CLEANUP3 + CONTRAST1.
The rejected DETAILCOPY R1 was never applied. All workers used
`gemini-3.8-flash-high`; proposals only, verification `NOT_RUN`.

Protected: form/controls/actions/options/rights/customer data, helper itself,
detail/history grids, dark Studio and both Hub count colors, backend, auth,
integration, Bot/engine, provider, wallet, ENV and motion.

| AC | Observable acceptance | Evidence |
|---|---|---|
|01|19 existing keys, 57 exact VI/EN/ZH values|Physical dictionary and actual renderer|
|02|Two boundary calls absent; no empty substitute|Source and full DOM comparator|
|03|Create grid one column and full width at375/1440|Computed layout, no overflow|
|04|Studio light counts ≥4.5; three other theme/family colors unchanged|Computed foreground/background and measured contrast|
|05|Form values/actions/rights/data/text outside approved changes preserved|Full candidate DOM vs BASE using identical candidate dictionary, only boundary/empty whitespace removed|
|06|Three physical sources equal BASE+23 records|Forward comparator independent of historical input inverses|
|07|No regression, exact CI/merge/deploy/runtime and asset proof|Separate local/CI/delivery receipts|

Current focused command:
`node --test tests/image-studio-presentation.test.mjs tests/image-studio-option-labels.test.mjs tests/image-studio-create-fields-locale.test.mjs`.
Python historical/bundle comparison uses the existing eight-file147-case set.
Workflow also executes the new physical-source test. Historical adapters
restore only exact approved values/removals/rules; unrelated bytes remain
observable and negative tests reject mixed records.

Local browser plugin absent: installed Playwright/Chrome with synthetic data,
all requests blocked, child-only temporary paths, no submit/auth/production.
The48-case matrix covers Studio/Hub × create/detail ×3locales ×2sizes ×2themes.
Its recorded comparator is PR793 tested HEAD
`ebecff2ff474d4d6414aaa2ef4ab47ba89310a2a`; delivered BASE above has the
identical full tree `ce06d5d307a18f816678b171910130abcbefb5b8`, confirmed by
both tree IDs and an empty full-tree diff. The artifact label is preserved.
No claim of image output or signed production interaction is made.
Merge and deployment only after local regression, review, documentation,
Tester handoff, provenance and exact-head CI pass.
