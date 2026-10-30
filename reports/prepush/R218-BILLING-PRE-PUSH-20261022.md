# R218 Billing UI — pre-push report (22/10/2026)

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=R218-BILLING-20261022
PRODUCT=TOAN AAS standalone WebApp
REPO=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=e5b1f5866867221f6ffd131a43f1644dc2c6249a
BRANCH=webapp-r218-billing-ui-20261022
ISSUE=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/660

## 1. Review code / operations docs

Allowed runtime files are `static/portal/portal.js`, `integration.js`,
`portal-i18n.js`, `portal.css`; tests cover billing metadata, manual top-up,
QR presentation, public-sale projection and Free Tools copy. No backend, Bot,
route-engine, schema, ENV, payment rule, provider or deployment workflow diff.

Changed behavior:

- PayOS top-up cards render only server `topup_packages`; empty server catalog
  renders zero client tiers and truthful empty copy.
- Payment options have their own `loading/ready/failed/guarded` state and a
  route-fenced GET retry. Manual history keeps its separate state and retry.
- ACB selector deduplicates only the customer presentation. It prefers a ready
  existing selection, then ready VietQR, then ready bank; canonical method IDs,
  history and server data remain unchanged.
- Portrait QR images keep intrinsic ratio and quiet zone. Desktop target is
  480px width/max520; mobile retains full image width and document overflow is 0.
- YouTube thumbnail labels describe available sizes without promising measured
  1080p/720p/360p dimensions.
- Legacy package note is localized to customer copy; it does not infer pricing,
  visibility or purchase authority.

Current operations docs updated:

- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`
- `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`
- `KIEM-THU/DANH-SACH-CASE.md`
- `MAP.md` and generated `MAP.html`
- `.agents/state/WEBAPP-BOT-PARITY-R218.yaml`
- `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`

## 2. Initial feature comparison

Source feature inventory used: `reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md`
and the historical crosswalk `reports/audit/WEBAPP-HISTORICAL-CHECKLIST-CROSSWALK-R218.md`.
The current product document is `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`.
The billing comparison records these measured differences:

| Source capability | Current Web evidence | Status |
|---|---|---|
| Top-up packages | API 0 browser fallback; only server rows render | Accepted UI contract |
| Manual payment | options/history separated; method + amount before QR | Accepted UI/control, no production transaction |
| Package catalog | 4 monthly + 20 combos; 24 cards after hydrate | Read-only accepted; prices upstream-pending |
| Public sale price | Requires approved SKU/version projection | Blocked when Core Bridge has no approved catalog |
| ACB/VietQR | One readiness-aware customer choice; IDs/history preserved | Browser verified in QA only |
| QR display | Natural portrait ratio; no transform/crop | Browser verified in QA only |

## 3. Tester workspace

Existing tester workspace is used; no competing project or issue was created.

- Tracking issue: [#660](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/660)
- Local case source: `KIEM-THU/DANH-SACH-CASE.md`
- Issue templates: `.github/ISSUE_TEMPLATE/01-case-test.yml`,
  `.github/ISSUE_TEMPLATE/02-bao-loi.yml`
- Tester guidance: `KIEM-THU/HUONG-DAN-TESTER.md`
- Evidence: `C:/Users/toann/Documents/Codex/qa/r218-billing-repair-packet/browser-result.json`
- Browser cases: 24 signed configurations × 5 metadata/ACB modes = 120 cases;
  errors 0, writes 0, external requests 0, overflow 0.
- QA account and fixture data are disposable; no credentials appear here.

## Verification

- Node suite: `902 passed, 0 failed`.
- Wallet truth: `21 passed, 16 warnings` in 20.06s, isolated DB + mocked bridge.
- Billing/QR/Python selected regression: `24 passed, 1 deselected` (CSS baseline
  test excluded only after same failure reproduced on BASE).
- Public sale pricing projection: `11 passed`.
- Billing locale/navigation: `7 passed`.
- Free Tools: `7 passed`.
- Browser: `120/120`, all target locales/themes/viewports; no writes/external/error.
- Syntax: portal.js, integration.js, portal-i18n.js exit 0.
- `git diff --check`: exit 0.

Known baseline comparators:

- `test_5_css_manual_topup_uses_aura_semantic_tokens_and_explicit_contrast`
  fails identically at BASE and candidate due pre-existing token parsing aliases.
- `test_billing_ui_uses_app_first_tokens_and_mobile_targets_without_new_gradients`
  fails identically at BASE and candidate due an existing Free Tools gradient in
  the broad CSS slice. No CSS outside QR presentation was changed.

## Safety gates

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_SECRET_CHANGES=0
BOT_DIFF=0
DEPLOY_WORKFLOW_DIFF=0
PUSH_GATE=READY_AFTER_REVIEW
LIVE_PASS=NOT_RUN_FOR_THIS_UNCOMMITTED_BATCH

The candidate has not been committed, pushed, merged or deployed in this report.
Production remains on the previously deployed PR654 revision until a delivery
step is authorized and executed with the exact reviewed SHA.
