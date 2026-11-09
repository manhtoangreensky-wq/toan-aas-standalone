# Phiên kiểm thử Motion — 09/11/2026

SESSION_ID=MOTION-SMOOTHNESS-20261109
STATUS=LOCAL_VERIFIED_PENDING_CI_DEPLOY_LIVE
BASE_SHA=b4e52fe1e6455714d034131a8f802aa8372e5a5f
ISSUE=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689
RECEIPT=../docs/reports/motion-20261109.md
PROVENANCE=../reports/migration/preflight.json
PRODUCTION_LIVE=NOT_TESTED

Nguồn case: [DANH-SACH-CASE.md](DANH-SACH-CASE.md), cụm MOTION-NOV09.
Sửa ca tại nguồn trước; không tạo Issue/PR trống hoặc dùng fixture làm LIVE.

- [x] ENTRY: callback dựng/enter cũ bị chặn; current/two-main/fallback/reduced giữ.
- [x] LANDING:8ca window/workspace, ngưỡng0/20/21/300; một snapshot, đọc trước ghi.
- [x] ARTICLE: native RED dashboard7/7/5,Studio3; bỏ rule chung, giữ entry riêng.
- [x] WORKSPACE:6ca, snapshot viewport trước class/style; cleanup/observer/focus giữ.
- [x] Focused65/65; fullNode1907/1907; Python18/18; syntax/compile/diff.
- [x] Final native12+focused6 đúng hash sau4patch; thường/giảm,390/1440; replay0,
  article18/18,Features2/2/menu12/12/navigation10/10/freshdocument18/18; error/overflow0.
- [x] Independent review0Critical/0Important; metadata32pass/1WindowsPOSIXdeselected;
  report/artifact và đối chiếu chức năng gốc đã có. Script/test POSIX giữ nguyên.
- [ ] Provenance và exact-head CI, gồm bài quyền POSIX trên Ubuntu.
- [ ] PR merge, deploy và đối chiếu SHA/services/assets VPS.
- [ ] Signed production/device smoothness; startup longtasks vẫn chưa đóng.

Lệnh Node:
```powershell
node --test tests/motion-replace-ownership.test.mjs tests/landing-scroll-read-order.test.cjs tests/workspace-motion-read-order.test.cjs tests/customer-entry-lifecycle.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs tests/current-main-motion-static-gates.test.mjs tests/publishing-main-motion-contract.test.mjs tests/customer-sidebar-hydration.test.mjs tests/landing-reduced-replay-cleanup.test.mjs
```

Native flow: app localhost với DB tạm → tải Dashboard/Features/Studio tại390/1440,
thường/giảm → đếm animationstart và đo article sau hydrate → cuộn → mở menu →
Escape/trả focus → bấm link Features/chờ tài liệu mới. Lặp Dashboard390 ba lần
mỗi chế độ. Không bấm tạo job, upload, payment/provider hoặc OAuth.
