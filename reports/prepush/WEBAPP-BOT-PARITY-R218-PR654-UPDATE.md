# Pre-push report — WEBAPP-BOT-PARITY-R218 / PR #654

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Identity

```text
REPOSITORY=manhtoangreensky-wq/toan-aas-standalone
BRANCH=webapp-r217-subdub-ui-r218
SOURCE_HEAD_SHA=148be4f6ec18e3c7fe3abfee8ca8a34ee1a5d099
DOCS_ONLY_UPDATE=true
PR=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/654
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

## 1. Review code và tài liệu vận hành

- Runtime SubDub presentation đã có ở `static/portal/portal.js` và `static/portal/portal.css`;
  lần cập nhật này không sửa runtime code, chỉ khóa evidence/checklist sau CI.
- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` và `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`
  đã bổ sung disposition hiện tại: lane presentation đạt, capability/execution/delivery
  vẫn mở.
- Completion ledger duy nhất là
  `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`; bảng B01–B34 trong
  `reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md` giữ toàn bộ phạm vi Voice, Music,
  SubDub, Image, Product Video/Video Editor, Utilities, AutoPost, Support, Account và Admin.

## 2. Evidence đã xác minh

```text
CI_RUN=39101124230
VERIFY_WEB_APP=SUCCESS
AUTHENTICATED_WEBAPP_QA=SUCCESS
ROUTE_RENDER_MATRIX=456/456
LOCAL_TARGETED=node --check static/portal/portal.js; node --test tests/subdub-hub-presentation.test.mjs => 13 passed, 0 failed
LOCAL_REGRESSION=full Node suite previously 527 passed, 0 failed on the same runtime HEAD
JSON_EVIDENCE=preflight.json + web_inventory.json parse successfully
MIGRATION_SOURCE_FILES=recorded in reports/migration/web_inventory.json
MIGRATION_SOURCE_FINGERPRINT=recorded in reports/migration/preflight.json and web_inventory.json
GIT_DIFF_CHECK=PASS
```

Route/render matrix chỉ chứng minh shell, locale, theme, viewport và browser QA isolated;
không chứng minh provider call, server capability, upload, quote, job, artifact output,
delivery hoặc LIVE production.

## 3. Tester workspace

- Nguồn case: `KIEM-THU/DANH-SACH-CASE.md`.
- Hướng dẫn: `KIEM-THU/HUONG-DAN-TESTER.md`.
- Issue templates: `.github/ISSUE_TEMPLATE/01-case-test.yml` và `02-bao-loi.yml`.
- Tracker/Project đã nghiệm thu trước đó: issue `#412`, project `TOAN AAS Web App · Tester P0`;
  không tạo issue/project cạnh tranh trong docs-only update.
- Tester phải đối chiếu đúng `SOURCE_HEAD_SHA`, route matrix `456/456`, SubDub targeted
  `13/13`, và giữ các protected comparator: Auth/Admin/Landing, locale VI/EN/ZH, theme,
  phone/tablet/desktop.

```text
TESTER_WORKSPACE=REUSE_EXISTING_ACCEPTED_WORKSPACE
EXTERNAL_MUTATION_IN_THIS_UPDATE=0
PUSH_GATE=READY_FOR_DOCUMENTATION_UPDATE
```

## 4. Disposition trước khi mở wave tiếp

- Đã khóa: SubDub lane selector, link Voice, ba callback riêng Auto 2/Multi 3–8/Smart Multi,
  dub volume static 0–200, locale copy và route/render CI evidence.
- Chưa khóa: Voice Vault mapping, Music editor/two-track delivery, SubDub server capability
  và execution, Image/Utilities/AutoPost/Admin control-level evidence, Product Video/Video
  Editor execution và toàn bộ motion cuối.
- Không merge, deploy, live hoặc gọi provider trong batch này.
